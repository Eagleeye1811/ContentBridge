import { useEffect, useMemo, useState } from 'react'
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

const LANGUAGE_NAME: Record<string, string> = { en: 'English', hi: 'हिन्दी', mr: 'मराठी' }

export default function OutputsPanel({ doc }: { doc: Doc }) {
  const [outputs, setOutputs] = useState<Output[] | null>(null)
  const [language, setLanguage] = useState('all')
  const [audience, setAudience] = useState('all')

  useEffect(() => {
    api.listOutputs(doc.id).then(setOutputs).catch(() => setOutputs([]))
  }, [doc.id])

  // Only the newest version of each (type, audience, language) is interesting.
  const current = useMemo(() => {
    const best = new Map<string, Output>()
    for (const o of outputs ?? []) {
      const key = `${o.type}|${o.audience}|${o.language}`
      const seen = best.get(key)
      if (!seen || o.version > seen.version) best.set(key, o)
    }
    return [...best.values()].sort(
      (a, b) => a.type.localeCompare(b.type) || a.language.localeCompare(b.language),
    )
  }, [outputs])

  const languages = useMemo(
    () => ['all', ...new Set(current.map((o) => o.language))],
    [current],
  )
  const audiences = useMemo(() => ['all', ...new Set(current.map((o) => o.audience))], [current])

  const visible = current.filter(
    (o) =>
      (language === 'all' || o.language === language) &&
      (audience === 'all' || o.audience === audience),
  )

  if (!outputs) return <p className="text-sm text-ink-400">Loading outputs…</p>

  if (current.length === 0) {
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
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="text-ink-600">
          {current.length} output{current.length === 1 ? '' : 's'} from one Source of Truth
        </span>
        <Pills label="Language" values={languages} active={language} onChange={setLanguage}
               display={(v) => (v === 'all' ? 'All' : (LANGUAGE_NAME[v] ?? v))} />
        <Pills label="Audience" values={audiences} active={audience} onChange={setAudience}
               display={(v) => (v === 'all' ? 'All' : v)} />
      </div>

      <ul className="divide-y divide-ink-200 overflow-hidden rounded-xl border border-ink-200 bg-white">
        {visible.map((o) => (
          <li key={o.id}>
            <Link to={`/outputs/${o.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-ink-50">
              <span className="w-28 shrink-0 text-sm font-medium">{o.type}</span>
              <span className="min-w-0 flex-1 truncate text-sm text-ink-600">
                {o.title || '(untitled)'}
              </span>
              <span className="rounded bg-ink-100 px-1.5 py-0.5 text-xs text-ink-600">
                {LANGUAGE_NAME[o.language] ?? o.language}
              </span>
              <span className="text-xs text-ink-400">
                {o.audience} · v{o.version}
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
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_TONE[o.status]}`}>
                {o.status}
              </span>
            </Link>
          </li>
        ))}
        {visible.length === 0 && (
          <li className="px-4 py-6 text-center text-sm text-ink-400">
            No outputs match this filter.
          </li>
        )}
      </ul>
    </div>
  )
}

function Pills({
  label,
  values,
  active,
  onChange,
  display,
}: {
  label: string
  values: string[]
  active: string
  onChange: (v: string) => void
  display: (v: string) => string
}) {
  if (values.length <= 2) return null
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-ink-400">{label}</span>
      {values.map((v) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`rounded-md px-2 py-0.5 text-xs ${
            v === active ? 'bg-ink-900 text-white' : 'bg-white text-ink-600 ring-1 ring-ink-200'
          }`}
        >
          {display(v)}
        </button>
      ))}
    </div>
  )
}
