import { useState } from 'react'
import { api, ApiError } from '@/api/client'
import { Button } from '@/components/ui'
import type { Evidence, Fact } from '@/types/api'

export const FACT_TYPE_LABEL: Record<Fact['type'], string> = {
  metric: 'Number',
  date: 'Date',
  entity: 'Name',
  finding: 'Finding',
  recommendation: 'Recommendation',
  risk: 'Risk',
}

const TYPE_TONE: Record<Fact['type'], string> = {
  metric: 'bg-blue-50 text-blue-700',
  date: 'bg-violet-50 text-violet-700',
  entity: 'bg-teal-50 text-teal-700',
  finding: 'bg-amber-50 text-amber-700',
  recommendation: 'bg-emerald-50 text-emerald-700',
  risk: 'bg-red-50 text-red-700',
}

interface Props {
  fact: Fact
  selected: boolean
  onSelectEvidence: (e: Evidence) => void
  onUpdated: (fact: Fact) => void
}

export default function FactCard({ fact, selected, onSelectEvidence, onUpdated }: Props) {
  const [editing, setEditing] = useState(false)
  const [statement, setStatement] = useState(fact.statement)
  const [value, setValue] = useState(fact.canonical_value ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateFact(fact.id, {
        statement,
        canonical_value: value.trim() === '' ? null : value.trim(),
      })
      onUpdated(updated)
      setEditing(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save')
    } finally {
      setSaving(false)
    }
  }

  const pages = [...new Map(fact.evidence.map((e) => [e.page_no, e])).values()]

  return (
    <div
      className={`rounded-xl border p-4 transition ${
        selected ? 'border-amber-400 bg-amber-50' : 'border-ink-200 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${TYPE_TONE[fact.type]}`}>
          {FACT_TYPE_LABEL[fact.type]}
        </span>
        {fact.edited_by_human && (
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
            Corrected
          </span>
        )}
        <button
          onClick={() => setEditing((v) => !v)}
          className="ml-auto text-xs font-medium text-ink-400 hover:text-ink-900"
        >
          {editing ? 'Cancel' : 'Correct'}
        </button>
      </div>

      {editing ? (
        <div className="mt-2 space-y-2">
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
          {fact.canonical_value !== null && (
            <label className="flex items-center gap-2 text-xs text-ink-600">
              Main figure
              <input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-36 rounded-lg border border-ink-200 px-2 py-1 text-sm outline-none focus:border-brand-500"
              />
            </label>
          )}
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : 'Save correction'}
            </Button>
            {error && <span className="text-xs text-red-700">{error}</span>}
          </div>
        </div>
      ) : (
        <p className="mt-2 text-sm leading-relaxed">{fact.statement}</p>
      )}

      {pages.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {pages.map((e) => (
            <button
              key={e.block_id}
              onClick={() => onSelectEvidence(e)}
              title={e.quote}
              className="rounded-full border border-ink-200 px-2 py-0.5 text-xs text-ink-600 hover:border-brand-500 hover:text-brand-600"
            >
              Page {e.page_no}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
