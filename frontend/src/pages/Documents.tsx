import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import UploadDropzone from '@/components/UploadDropzone'
import type { Doc } from '@/types/api'

export default function Documents() {
  const [docs, setDocs] = useState<Doc[]>([])
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const refresh = useCallback(() => {
    api
      .listDocuments()
      .then(setDocs)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load documents'))
  }, [])

  useEffect(refresh, [refresh])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Documents</h2>
        <p className="text-sm text-ink-600">
          Upload an authoritative source. Every block it contains becomes citable.
        </p>
      </div>

      <UploadDropzone
        onComplete={(id) => {
          refresh()
          navigate(`/documents/${id}`)
        }}
      />

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {docs.length === 0 ? (
        <p className="text-sm text-ink-400">No documents yet.</p>
      ) : (
        <ul className="divide-y divide-ink-200 overflow-hidden rounded-xl border border-ink-200 bg-white">
          {docs.map((d) => (
            <li key={d.id}>
              <Link
                to={`/documents/${d.id}`}
                className="flex items-center gap-4 px-4 py-3 hover:bg-ink-50"
              >
                <span className="min-w-0 flex-1 truncate text-sm font-medium">{d.filename}</span>
                <span className="text-xs text-ink-400">
                  {d.page_count} pg · {(d.size_bytes / 1024).toFixed(0)} KB
                </span>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    d.status === 'failed'
                      ? 'bg-red-100 text-red-700'
                      : d.status === 'parsed' || d.status === 'ready'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-ink-200 text-ink-600'
                  }`}
                >
                  {d.status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
