import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/api/client'
import type { Doc, Output } from '@/types/api'

const STATUS_TONE: Record<Output['status'], string> = {
  draft: 'bg-ink-200 text-ink-600',
  verified: 'bg-blue-100 text-blue-700',
  in_review: 'bg-amber-100 text-amber-700',
  approved: 'bg-emerald-100 text-emerald-700',
  rejected: 'bg-red-100 text-red-700',
  exported: 'bg-violet-100 text-violet-700',
}

export default function OutputsPanel({ doc }: { doc: Doc }) {
  const [outputs, setOutputs] = useState<Output[] | null>(null)

  useEffect(() => {
    api.listOutputs(doc.id).then(setOutputs).catch(() => setOutputs([]))
  }, [doc.id])

  if (!outputs) return <p className="text-sm text-ink-400">Loading outputs…</p>

  if (outputs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-10 text-center">
        <p className="text-sm font-medium">Nothing generated yet</p>
        <p className="mt-1 text-sm text-ink-600">
          Use the Studio tab to produce outputs from this document&apos;s Source of Truth.
        </p>
      </div>
    )
  }

  return (
    <ul className="divide-y divide-ink-200 overflow-hidden rounded-xl border border-ink-200 bg-white">
      {outputs.map((o) => (
        <li key={o.id}>
          <Link to={`/outputs/${o.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-ink-50">
            <span className="w-24 shrink-0 text-sm font-medium">{o.type}</span>
            <span className="min-w-0 flex-1 truncate text-sm text-ink-600">
              {o.title || '(untitled)'}
            </span>
            <span className="text-xs text-ink-400">
              {o.audience} · {o.language} · v{o.version}
            </span>
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_TONE[o.status]}`}>
              {o.status}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
