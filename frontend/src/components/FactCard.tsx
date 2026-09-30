import { useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { Evidence, Fact } from '@/types/api'

const TYPE_TONE: Record<Fact['type'], string> = {
  metric: 'bg-blue-100 text-blue-700',
  date: 'bg-violet-100 text-violet-700',
  entity: 'bg-teal-100 text-teal-700',
  finding: 'bg-amber-100 text-amber-700',
  recommendation: 'bg-emerald-100 text-emerald-700',
  risk: 'bg-red-100 text-red-700',
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

  return (
    <div
      className={`rounded-lg border p-3 transition ${
        selected ? 'border-amber-400 bg-amber-50' : 'border-ink-200 bg-white'
      }`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${TYPE_TONE[fact.type]}`}>
          {fact.type}
        </span>
        {fact.canonical_value && (
          <span className="rounded bg-ink-900 px-1.5 py-0.5 font-mono text-xs text-white">
            {fact.canonical_value}
            {fact.unit === 'percent' ? '%' : ''}
          </span>
        )}
        {fact.unit && fact.unit !== 'percent' && (
          <span className="text-xs text-ink-400">{fact.unit}</span>
        )}
        {fact.edited_by_human && (
          <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-700">
            edited
          </span>
        )}
        <button
          onClick={() => setEditing((v) => !v)}
          className="ml-auto text-xs text-ink-400 hover:text-ink-900"
        >
          {editing ? 'Cancel' : 'Edit'}
        </button>
      </div>

      {editing ? (
        <div className="mt-2 space-y-2">
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-ink-200 px-2 py-1.5 text-sm outline-none focus:border-brand-500"
          />
          <div className="flex items-center gap-2">
            <label className="text-xs text-ink-600">Canonical value</label>
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              className="w-32 rounded-lg border border-ink-200 px-2 py-1 font-mono text-sm outline-none focus:border-brand-500"
            />
            <button
              onClick={save}
              disabled={saving}
              className="ml-auto rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-500 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
          <p className="text-xs text-ink-400">
            Correcting a fact corrects every output generated from it afterwards.
          </p>
          {error && <p className="text-xs text-red-700">{error}</p>}
        </div>
      ) : (
        <p className="mt-1.5 text-sm">{fact.statement}</p>
      )}

      <div className="mt-2 flex flex-wrap gap-1">
        {fact.evidence.map((e) => (
          <button
            key={e.block_id}
            onClick={() => onSelectEvidence(e)}
            title={e.quote}
            className="rounded border border-ink-200 bg-ink-50 px-1.5 py-0.5 text-xs text-ink-600 hover:border-brand-500 hover:text-brand-600"
          >
            p{e.page_no} · {e.section_path.split(' > ').pop() || 'source'}
          </button>
        ))}
      </div>
    </div>
  )
}
