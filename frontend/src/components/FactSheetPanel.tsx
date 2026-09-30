import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '@/api/client'
import DocumentViewer from '@/components/DocumentViewer'
import FactCard from '@/components/FactCard'
import type { Block, Doc, Evidence, Fact, FactSheet } from '@/types/api'

interface Props {
  doc: Doc
  blocks: Block[]
}

export default function FactSheetPanel({ doc, blocks }: Props) {
  const [sheet, setSheet] = useState<FactSheet | null>(null)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [page, setPage] = useState(1)
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string>('all')

  useEffect(() => {
    api
      .getFactSheet(doc.id)
      .then((s) => {
        setSheet(s)
        setMissing(false)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setMissing(true)
        else setError(err instanceof Error ? err.message : 'Failed to load fact sheet')
      })
  }, [doc.id])

  async function runExtraction() {
    setRunning(true)
    setError(null)
    try {
      const job = await api.runExtraction(doc.id)
      const final = await api.streamJob(job.id, () => {})
      if (final.status === 'failed') {
        setError(final.error ?? 'Extraction failed')
        return
      }
      setSheet(await api.getFactSheet(doc.id))
      setMissing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed')
    } finally {
      setRunning(false)
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

  if (error && !sheet) {
    return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
  }

  if (missing) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-10 text-center">
        <p className="text-sm font-medium">No Source of Truth extracted yet</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-ink-600">
          Extraction reads the indexed document and produces facts that each cite the blocks they
          came from. Facts that cannot be traced to a real block are discarded.
        </p>
        <button
          onClick={runExtraction}
          disabled={running}
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50"
        >
          {running ? 'Extracting…' : 'Extract Source of Truth'}
        </button>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      </div>
    )
  }

  if (!sheet) return <p className="text-sm text-ink-400">Loading fact sheet…</p>

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">
          {sheet.facts.length} fact{sheet.facts.length === 1 ? '' : 's'}
        </span>
        <span className="text-ink-400">
          v{sheet.version} · {sheet.model}
        </span>
        <div className="flex flex-wrap gap-1">
          {types.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-md px-2 py-0.5 text-xs ${
                t === typeFilter ? 'bg-ink-900 text-white' : 'bg-white text-ink-600 hover:bg-ink-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <button
          onClick={runExtraction}
          disabled={running}
          className="ml-auto rounded-lg border border-ink-200 px-3 py-1.5 text-xs font-medium hover:border-ink-400 disabled:opacity-50"
        >
          {running ? 'Re-extracting…' : 'Re-extract'}
        </button>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="max-h-[75vh] space-y-2 overflow-y-auto pr-1">
          {visible.length === 0 && <p className="text-sm text-ink-400">No facts of this type.</p>}
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

        <div className="lg:sticky lg:top-4 lg:self-start">
          <DocumentViewer
            doc={doc}
            page={page}
            blocks={pageBlocks}
            selectedId={selectedBlockId}
            onSelect={setSelectedBlockId}
          />
          <p className="mt-2 text-xs text-ink-400">
            Click a citation chip to jump to the exact place in the source that supports it.
          </p>
        </div>
      </div>
    </div>
  )
}
