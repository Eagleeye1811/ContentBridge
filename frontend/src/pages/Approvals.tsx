import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import { useAuth } from '@/lib/auth'
import type { PendingOutput } from '@/types/api'

export default function Approvals() {
  const { user } = useAuth()
  const [queue, setQueue] = useState<PendingOutput[] | null>(null)

  useEffect(() => {
    api.reviewQueue().then(setQueue).catch(() => setQueue([]))
  }, [])

  if (!queue) return <p className="text-sm text-ink-400">Loading queue…</p>

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Approvals</h2>
        <p className="text-sm text-ink-600">
          {user?.role === 'approver'
            ? 'Everything submitted for review. An output with a contradicted claim cannot be approved until it is resolved.'
            : 'Your outputs awaiting a decision, and anything sent back to you.'}
        </p>
      </div>

      {queue.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink-200 bg-white p-10 text-center">
          <p className="text-sm font-medium">Nothing waiting</p>
          <p className="mt-1 text-sm text-ink-600">
            Verify an output and submit it for review to see it here.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-ink-200 overflow-hidden rounded-xl border border-ink-200 bg-white">
          {queue.map((o) => (
            <li key={o.id}>
              <Link to={`/outputs/${o.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-ink-50">
                <span className="w-28 shrink-0 text-sm font-medium">{o.type}</span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm">{o.title || '(untitled)'}</span>
                  <span className="text-xs text-ink-400">{o.document_name}</span>
                </span>
                <span className="text-xs text-ink-400">
                  {o.audience} · {o.language} · v{o.version}
                </span>
                {o.trust_score !== null && (
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
                      o.trust_score >= 0.85
                        ? 'bg-emerald-100 text-emerald-700'
                        : o.trust_score >= 0.6
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {Math.round(o.trust_score * 100)}%
                  </span>
                )}
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    o.status === 'rejected'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {o.status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
