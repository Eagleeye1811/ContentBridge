import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import AddSource from '@/components/AddSource'
import { Badge, Button, Empty, PageHeader } from '@/components/ui'
import { Icon } from '@/lib/icons'
import { DOC_STATUS, sourceKind, timeAgo } from '@/lib/labels'
import type { Doc } from '@/types/api'

export default function Sources() {
  const [docs, setDocs] = useState<Doc[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<string | null>(null)
  const navigate = useNavigate()

  const refresh = useCallback(() => {
    api
      .listDocuments()
      .then(setDocs)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load sources'))
  }, [])

  useEffect(refresh, [refresh])

  async function remove(id: string) {
    try {
      await api.deleteDocument(id)
      setConfirming(null)
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete')
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="Sources"
        subtitle="Start with a trusted document. Create advisories, presentations, posts and more from it."
      />

      <AddSource
        onComplete={(id) => {
          refresh()
          navigate(`/sources/${id}`)
        }}
      />

      {error && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
      )}

      <h2 className="mb-3 mt-8 text-sm font-semibold text-ink-600">Your sources</h2>
      {docs === null ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : docs.length === 0 ? (
        <Empty title="No sources yet" icon={<Icon name="document" />}>
          Add a document, an image or some text above to get started.
        </Empty>
      ) : (
        <ul className="space-y-2">
          {docs.map((d) => {
            const status = DOC_STATUS[d.status] ?? { label: d.status, tone: 'neutral' as const }
            return (
              <li
                key={d.id}
                className="flex items-center gap-4 rounded-2xl border border-ink-200 bg-white p-4 shadow-sm transition hover:border-ink-400"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ink-100 text-ink-600">
                  <Icon
                    name={d.mime.startsWith('image/') ? 'image' : d.mime.startsWith('text/') ? 'text' : 'document'}
                  />
                </span>
                <Link to={`/sources/${d.id}`} className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{d.filename}</span>
                  <span className="text-xs text-ink-400">
                    {sourceKind(d.mime)} · added {timeAgo(d.created_at)}
                  </span>
                </Link>
                <Badge tone={status.tone}>{status.label}</Badge>
                {confirming === d.id ? (
                  <span className="flex items-center gap-2">
                    <span className="hidden text-xs text-ink-600 sm:inline">
                      Delete it and everything made from it?
                    </span>
                    <Button size="sm" variant="danger" onClick={() => remove(d.id)}>
                      Delete
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setConfirming(null)}>
                      Cancel
                    </Button>
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <Link
                      to={`/sources/${d.id}`}
                      className="rounded-lg px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-blue-50"
                    >
                      Open
                    </Link>
                    <button
                      onClick={() => setConfirming(d.id)}
                      title="Delete source"
                      className="rounded-lg p-2 text-ink-400 hover:bg-red-50 hover:text-red-700"
                    >
                      <Icon name="trash" />
                    </button>
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
