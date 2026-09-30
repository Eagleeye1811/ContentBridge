import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '@/api/client'
import ContentIRView from '@/components/ContentIRView'
import ApprovalPanel from '@/components/ApprovalPanel'
import ExportBar from '@/components/ExportBar'
import VerificationPanel from '@/components/VerificationPanel'
import type { ContentIR, Fact, OutputDetail } from '@/types/api'

export default function OutputReview() {
  const { id = '' } = useParams()
  const [output, setOutput] = useState<OutputDetail | null>(null)
  const [draft, setDraft] = useState<ContentIR | null>(null)
  const [selectedFactId, setSelectedFactId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    api
      .getOutput(id)
      .then((o) => {
        setOutput(o)
        setDraft(o.content_ir)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [id])

  useEffect(load, [load])

  const facts = useMemo(
    () => new Map<string, Fact>((output?.facts ?? []).map((f) => [f.id, f])),
    [output],
  )
  const selectedFact = selectedFactId ? facts.get(selectedFactId) : undefined
  const dirty = draft !== null && output !== null && draft !== output.content_ir

  async function save() {
    if (!draft) return
    setBusy(true)
    setError(null)
    try {
      const updated = await api.updateOutput(id, draft)
      setOutput(updated)
      setDraft(updated.content_ir)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save')
    } finally {
      setBusy(false)
    }
  }

  if (error && !output) {
    return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
  }
  if (!output || !draft) return <p className="text-sm text-ink-400">Loading…</p>

  const unresolved = draft.nodes.flatMap((n) => n.fact_ids).filter((f) => !facts.has(f)).length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Link
          to={`/documents/${output.document_id}/outputs`}
          className="text-sm text-ink-400 hover:text-ink-900"
        >
          ← Outputs
        </Link>
        <h2 className="text-lg font-semibold capitalize">{output.type}</h2>
        <span className="text-sm text-ink-600">
          {output.audience} · {output.language} · v{output.version} · {output.model}
        </span>
        <span className="rounded bg-ink-200 px-2 py-0.5 text-xs font-medium text-ink-600">
          {output.status}
        </span>
        <div className="ml-auto flex gap-2">
          <ExportBar
            outputId={id}
            filenameStem={`${output.type}_${output.audience}_${output.language}_v${output.version}`}
            renderers={output.renderers}
            onError={setError}
          />
          <button
            onClick={save}
            disabled={!dirty || busy}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-500 disabled:opacity-50"
          >
            {busy ? 'Saving…' : 'Save edits'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs">
        <span className="text-ink-600">
          {draft.nodes.length} nodes · {facts.size} facts cited
        </span>
        {unresolved > 0 ? (
          <span className="rounded bg-red-100 px-2 py-0.5 font-medium text-red-700">
            {unresolved} unresolved citation{unresolved === 1 ? '' : 's'}
          </span>
        ) : (
          <span className="rounded bg-emerald-100 px-2 py-0.5 font-medium text-emerald-700">
            every claim traced to the source
          </span>
        )}
        <span className="ml-auto text-ink-400">Every figure is checked against the source.</span>
      </div>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="rounded-xl border border-ink-200 bg-white p-5">
          <ContentIRView
            ir={draft}
            facts={facts}
            selectedFactId={selectedFactId}
            onSelectFact={setSelectedFactId}
          />
        </div>

        <div className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <ApprovalPanel outputId={id} onChanged={load} />
          <VerificationPanel
            outputId={id}
            onVerified={load}
            onFocusNode={(nodeId) =>
              document.getElementById(`ir-${nodeId}`)?.scrollIntoView({ block: 'center' })
            }
          />
          <Editor draft={draft} onChange={setDraft} />
          <EvidencePanel fact={selectedFact} />
        </div>
      </div>
    </div>
  )
}

function Editor({ draft, onChange }: { draft: ContentIR; onChange: (ir: ContentIR) => void }) {
  const [openId, setOpenId] = useState<string | null>(null)

  function patch(nodeId: string, update: Partial<ContentIR['nodes'][number]>) {
    onChange({
      ...draft,
      nodes: draft.nodes.map((n) => (n.id === nodeId ? { ...n, ...update } : n)),
    })
  }

  return (
    <div className="rounded-xl border border-ink-200 bg-white p-3">
      <p className="text-sm font-semibold">Edit</p>
      <p className="mt-0.5 text-xs text-ink-600">
        You edit the structure, not rendered text — so every export stays consistent.
      </p>
      <div className="mt-2 space-y-1">
        {draft.nodes.map((node) => (
          <div key={node.id} className="rounded-lg border border-ink-200">
            <button
              onClick={() => setOpenId(openId === node.id ? null : node.id)}
              className="flex w-full items-center gap-2 px-2 py-1.5 text-left text-xs hover:bg-ink-50"
            >
              <span className="rounded bg-ink-200 px-1.5 py-0.5 font-medium text-ink-600">
                {node.kind}
              </span>
              <span className="min-w-0 flex-1 truncate text-ink-600">
                {node.text ?? node.title ?? node.items?.[0] ?? '—'}
              </span>
            </button>
            {openId === node.id && (
              <div className="border-t border-ink-200 p-2">
                {node.items ? (
                  <textarea
                    value={node.items.join('\n')}
                    onChange={(e) => patch(node.id, { items: e.target.value.split('\n') })}
                    rows={Math.max(3, node.items.length)}
                    className="w-full rounded border border-ink-200 px-2 py-1 text-sm outline-none focus:border-brand-500"
                  />
                ) : (
                  <textarea
                    value={node.text ?? node.title ?? ''}
                    onChange={(e) =>
                      patch(node.id, node.text !== null && node.text !== undefined
                        ? { text: e.target.value }
                        : { title: e.target.value })
                    }
                    rows={3}
                    className="w-full rounded border border-ink-200 px-2 py-1 text-sm outline-none focus:border-brand-500"
                  />
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function EvidencePanel({ fact }: { fact: Fact | undefined }) {
  if (!fact) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-4 text-sm text-ink-400">
        Click a citation chip to see the source text behind it.
      </div>
    )
  }
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-4">
      <p className="text-sm font-semibold">Evidence</p>
      <p className="mt-1 text-sm">{fact.statement}</p>
      {fact.canonical_value && (
        <p className="mt-1.5 font-mono text-xs text-ink-600">
          canonical value: {fact.canonical_value}
          {fact.unit ? ` (${fact.unit})` : ''}
        </p>
      )}
      <div className="mt-3 space-y-2">
        {fact.evidence.map((e) => (
          <div key={e.block_id} className="rounded-lg bg-ink-50 p-2">
            <p className="text-xs text-ink-400">
              page {e.page_no} · {e.section_path}
            </p>
            <p className="mt-1 text-sm">{e.quote}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
