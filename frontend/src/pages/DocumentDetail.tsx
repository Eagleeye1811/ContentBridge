import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '@/api/client'
import DocumentViewer from '@/components/DocumentViewer'
import FactSheetPanel from '@/components/FactSheetPanel'
import OutputsPanel from '@/components/OutputsPanel'
import StudioPanel from '@/components/StudioPanel'
import type { Block, Doc } from '@/types/api'

export default function DocumentDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const tab: 'source' | 'facts' | 'studio' | 'outputs' = pathname.endsWith('/facts')
    ? 'facts'
    : pathname.endsWith('/studio')
      ? 'studio'
      : pathname.endsWith('/outputs')
        ? 'outputs'
        : 'source'

  const [doc, setDoc] = useState<Doc | null>(null)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.getDocument(id), api.listBlocks(id)])
      .then(([d, bs]) => {
        setDoc(d)
        setBlocks(bs)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
  }, [id])

  if (error) {
    return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
  }
  if (!doc) return <p className="text-sm text-ink-400">Loading…</p>

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <Link to="/documents" className="text-sm text-ink-400 hover:text-ink-900">
          ← Documents
        </Link>
        <h2 className="text-lg font-semibold">{doc.filename}</h2>
        <span className="text-sm text-ink-600">
          {doc.page_count} page{doc.page_count === 1 ? '' : 's'} · {blocks.length} blocks
        </span>
        <StatusChip status={doc.status} />
      </div>

      <div className="flex gap-1 border-b border-ink-200">
        {(
          [
            ['source', 'Source', `/documents/${id}`],
            ['facts', 'Source of Truth', `/documents/${id}/facts`],
            ['studio', 'Studio', `/documents/${id}/studio`],
            ['outputs', 'Outputs', `/documents/${id}/outputs`],
          ] as const
        ).map(([key, label, to]) => (
          <button
            key={key}
            onClick={() => navigate(to)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              tab === key
                ? 'border-ink-900 font-medium text-ink-900'
                : 'border-transparent text-ink-600 hover:text-ink-900'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'facts' && <FactSheetPanel doc={doc} blocks={blocks} />}
      {tab === 'studio' && <StudioPanel doc={doc} />}
      {tab === 'outputs' && <OutputsPanel doc={doc} />}
      {tab === 'source' && <SourceTab doc={doc} blocks={blocks} />}
    </div>
  )
}

function SourceTab({ doc, blocks }: { doc: Doc; blocks: Block[] }) {
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const pageBlocks = useMemo(() => blocks.filter((b) => b.page_no === page), [blocks, page])

  const select = useCallback((blockId: string) => {
    setSelectedId(blockId)
    document.getElementById(`block-${blockId}`)?.scrollIntoView({ block: 'nearest' })
  }, [])

  return (
    <div className="space-y-4">
      {doc.page_count > 1 && (
        <div className="flex flex-wrap gap-1">
          {Array.from({ length: doc.page_count }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`rounded-md px-2.5 py-1 text-sm ${
                p === page ? 'bg-ink-900 text-white' : 'bg-white text-ink-600 hover:bg-ink-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="max-h-[75vh] space-y-1.5 overflow-y-auto pr-1">
          {pageBlocks.length === 0 && (
            <p className="text-sm text-ink-400">No blocks extracted on this page.</p>
          )}
          {pageBlocks.map((b) => (
            <button
              key={b.id}
              id={`block-${b.id}`}
              onClick={() => setSelectedId(b.id)}
              className={`block w-full rounded-lg border p-3 text-left transition ${
                b.id === selectedId
                  ? 'border-amber-400 bg-amber-50'
                  : 'border-ink-200 bg-white hover:border-ink-400'
              }`}
            >
              <div className="flex items-center gap-2 text-xs text-ink-400">
                <span className="rounded bg-ink-200 px-1.5 py-0.5 font-medium text-ink-600">
                  {b.block_type}
                </span>
                <span className="truncate">{b.section_path || '—'}</span>
              </div>
              <p className="mt-1.5 text-sm">{b.text}</p>
            </button>
          ))}
        </div>

        <div className="lg:sticky lg:top-4 lg:self-start">
          <DocumentViewer
            doc={doc}
            page={page}
            blocks={pageBlocks}
            selectedId={selectedId}
            onSelect={select}
          />
          <p className="mt-2 text-xs text-ink-400">
            Click a block on either side — every block resolves to a page, a section and a box on
            the source.
          </p>
        </div>
      </div>
    </div>
  )
}

function StatusChip({ status }: { status: Doc['status'] }) {
  const tone =
    status === 'failed'
      ? 'bg-red-100 text-red-700'
      : status === 'ready'
        ? 'bg-emerald-100 text-emerald-700'
        : status === 'parsed' || status === 'indexed'
          ? 'bg-blue-100 text-blue-700'
          : 'bg-ink-200 text-ink-600'
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${tone}`}>{status}</span>
}
