import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import DocumentViewer from '@/components/DocumentViewer'
import { Button, Notice, PageHeader } from '@/components/ui'
import { Icon } from '@/lib/icons'
import { useWorkspace } from '@/pages/workspace/Workspace'

export default function DocumentPage() {
  const { doc, blocks } = useWorkspace()
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const pageBlocks = useMemo(() => blocks.filter((b) => b.page_no === page), [blocks, page])

  const select = useCallback((blockId: string) => {
    setSelectedId(blockId)
    document.getElementById(`block-${blockId}`)?.scrollIntoView({ block: 'nearest' })
  }, [])

  return (
    <div>
      <PageHeader
        title="Document"
        subtitle="The original source. Click any passage to see where it sits on the page."
        icon={<Icon name="document" className="h-5 w-5" />}
        action={
          <Link to={`/sources/${doc.id}/facts`}>
            <Button variant="secondary">
              <Icon name="facts" />
              View key facts
            </Button>
          </Link>
        }
      />

      {doc.status === 'failed' && (
        <div className="mb-4">
          <Notice tone="bad">We could not read this source. {doc.error}</Notice>
        </div>
      )}

      {doc.page_count > 1 && (
        <div className="mb-4 flex flex-wrap items-center gap-1">
          <span className="mr-2 text-sm text-ink-600">Page</span>
          {Array.from({ length: doc.page_count }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={`h-8 min-w-8 rounded-lg px-2 text-sm ${
                p === page ? 'bg-ink-900 text-white' : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <div className="max-h-[75vh] space-y-2 overflow-y-auto pr-1">
          {pageBlocks.length === 0 && (
            <p className="text-sm text-ink-400">No text was found on this page.</p>
          )}
          {pageBlocks.map((b) => (
            <button
              key={b.id}
              id={`block-${b.id}`}
              onClick={() => setSelectedId(b.id)}
              className={`block w-full rounded-xl border p-3 text-left transition ${
                b.id === selectedId
                  ? 'border-amber-400 bg-amber-50'
                  : 'border-ink-200 bg-white hover:border-ink-400'
              }`}
            >
              {b.section_path && (
                <p className="mb-1 truncate text-xs text-ink-400">{b.section_path}</p>
              )}
              <p
                className={`text-sm ${b.block_type === 'heading' ? 'font-semibold' : 'leading-relaxed'}`}
              >
                {b.text}
              </p>
            </button>
          ))}
        </div>

        <div className="xl:sticky xl:top-20 xl:self-start">
          <DocumentViewer
            doc={doc}
            page={page}
            blocks={pageBlocks}
            selectedId={selectedId}
            onSelect={select}
          />
        </div>
      </div>
    </div>
  )
}
