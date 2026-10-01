import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '@/api/client'
import DocumentViewer from '@/components/DocumentViewer'
import FactCard, { FACT_TYPE_LABEL } from '@/components/FactCard'
import { Button, Empty, Notice, PageHeader, Progress } from '@/components/ui'
import { friendlyStage } from '@/components/AddSource'
import { Icon } from '@/lib/icons'
import { useWorkspace } from '@/pages/workspace/Workspace'
import type { Evidence, Fact, FactSheet, Job } from '@/types/api'

export default function FactsPage() {
  const { doc, blocks, reloadDoc } = useWorkspace()
  const [sheet, setSheet] = useState<FactSheet | null>(null)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [running, setRunning] = useState(false)
  const [page, setPage] = useState(1)
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState('all')

  useEffect(() => {
    api
      .getFactSheet(doc.id)
      .then((s) => {
        setSheet(s)
        setMissing(false)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setMissing(true)
        else setError(err instanceof Error ? err.message : 'Could not load key facts')
      })
  }, [doc.id])

  async function findFacts() {
    setRunning(true)
    setError(null)
    try {
      const started = await api.runExtraction(doc.id)
      const final = await api.streamJob(started.id, setJob)
      if (final.status === 'failed') {
        setError(final.error ?? 'Could not find key facts')
        return
      }
      setSheet(await api.getFactSheet(doc.id))
      setMissing(false)
      reloadDoc()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not find key facts')
    } finally {
      setRunning(false)
      setJob(null)
    }
  }

  const types = useMemo(
    () => ['all', ...Array.from(new Set(sheet?.facts.map((f) => f.type) ?? []))],
    [sheet],
  )
  const visible = useMemo(
    () => (sheet?.facts ?? []).filter((f) => typeFilter === 'all' || f.type === typeFilter),
    [sheet, typeFilter],
  )
  const pageBlocks = useMemo(() => blocks.filter((b) => b.page_no === page), [blocks, page])

  function jumpTo(e: Evidence) {
    setPage(e.page_no)
    setSelectedBlockId(e.block_id)
  }

  function replaceFact(updated: Fact) {
    setSheet((s) =>
      s ? { ...s, facts: s.facts.map((f) => (f.id === updated.id ? updated : f)) } : s,
    )
  }

  const header = (
    <PageHeader
      title="Key facts"
      subtitle="Everything you create is written only from these facts. Correct one here and new content uses the correction."
      icon={<Icon name="facts" className="h-5 w-5" />}
      action={
        sheet && (
          <Button variant="secondary" onClick={findFacts} disabled={running}>
            {running ? 'Reading again…' : 'Read again'}
          </Button>
        )
      }
    />
  )

  if (missing || running) {
    return (
      <div>
        {header}
        {running ? (
          <div className="rounded-2xl border border-ink-200 bg-white p-8">
            <Progress value={job?.progress ?? 0.05} label={friendlyStage(job?.stage ?? 'extracting')} />
          </div>
        ) : (
          <Empty title="No key facts yet" icon={<Icon name="facts" />}>
            <p>We need to read the source and pick out its facts before you can create anything.</p>
            <div className="mt-4">
              <Button onClick={findFacts}>Find key facts</Button>
            </div>
          </Empty>
        )}
        {error && (
          <div className="mt-4">
            <Notice tone="bad">{error}</Notice>
          </div>
        )}
      </div>
    )
  }

  if (error && !sheet) return <Notice tone="bad">{error}</Notice>
  if (!sheet) return <p className="text-sm text-ink-400">Loading…</p>

  return (
    <div>
      {header}

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-sm font-medium">
          {sheet.facts.length} fact{sheet.facts.length === 1 ? '' : 's'}
        </span>
        {types.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`rounded-full px-3 py-1 text-xs ${
              t === typeFilter
                ? 'bg-ink-900 text-white'
                : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
            }`}
          >
            {t === 'all' ? 'All' : (FACT_TYPE_LABEL[t as Fact['type']] ?? t)}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4">
          <Notice tone="bad">{error}</Notice>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <div className="max-h-[75vh] space-y-2 overflow-y-auto pr-1">
          {visible.map((f) => (
            <FactCard
              key={f.id}
              fact={f}
              selected={f.evidence.some((e) => e.block_id === selectedBlockId)}
              onSelectEvidence={jumpTo}
              onUpdated={replaceFact}
            />
          ))}
        </div>
        <div className="xl:sticky xl:top-20 xl:self-start">
          <DocumentViewer
            doc={doc}
            page={page}
            blocks={pageBlocks}
            selectedId={selectedBlockId}
            onSelect={setSelectedBlockId}
          />
          <p className="mt-2 text-xs text-ink-400">
            Click “Page …” on a fact to see exactly where it comes from.
          </p>
        </div>
      </div>
    </div>
  )
}
