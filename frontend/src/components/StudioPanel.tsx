import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '@/api/client'
import type { Catalog, Doc, Job } from '@/types/api'

export default function StudioPanel({ doc }: { doc: Doc }) {
  const navigate = useNavigate()
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [types, setTypes] = useState<string[]>(['advisory'])
  const [audience, setAudience] = useState('officer')
  const [languages, setLanguages] = useState<string[]>(['en'])
  const [job, setJob] = useState<Job | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.catalog().then(setCatalog).catch(() => setCatalog(null))
  }, [])

  function toggle(list: string[], set: (v: string[]) => void, key: string) {
    set(list.includes(key) ? list.filter((k) => k !== key) : [...list, key])
  }

  async function run() {
    setError(null)
    try {
      const started = await api.generate(doc.id, { types, audience, languages })
      setJob(started)
      const final = await api.streamJob(started.id, setJob)
      if (final.status === 'failed') {
        setError(final.error ?? 'Generation failed')
        return
      }
      navigate(`/documents/${doc.id}/outputs`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Generation failed')
    } finally {
      setJob(null)
    }
  }

  if (!catalog) return <p className="text-sm text-ink-400">Loading catalog…</p>

  const total = types.length * languages.length
  const busy = job !== null

  return (
    <div className="max-w-3xl space-y-6">
      <p className="text-sm text-ink-600">
        Every output below is produced by the same generator from the same Source of Truth. They
        differ only by format spec, audience and language.
      </p>

      <Field label="Output types">
        <div className="grid gap-2 sm:grid-cols-2">
          {catalog.formats.map((f) => (
            <button
              key={f.key}
              onClick={() => toggle(types, setTypes, f.key)}
              className={`rounded-lg border p-3 text-left transition ${
                types.includes(f.key)
                  ? 'border-brand-500 bg-blue-50'
                  : 'border-ink-200 bg-white hover:border-ink-400'
              }`}
            >
              <p className="text-sm font-medium">{f.name}</p>
              <p className="mt-0.5 text-xs text-ink-600">{f.description}</p>
            </button>
          ))}
        </div>
      </Field>

      <Field label="Audience">
        <div className="flex flex-wrap gap-1.5">
          {catalog.audiences.map((a) => (
            <button
              key={a.key}
              onClick={() => setAudience(a.key)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                audience === a.key
                  ? 'bg-ink-900 text-white'
                  : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
              }`}
            >
              {a.name}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Languages">
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(catalog.languages).map(([code, name]) => (
            <button
              key={code}
              onClick={() => toggle(languages, setLanguages, code)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                languages.includes(code)
                  ? 'bg-ink-900 text-white'
                  : 'bg-white text-ink-600 ring-1 ring-ink-200 hover:ring-ink-400'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      </Field>

      {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={busy || total === 0}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50"
        >
          {busy ? (job?.stage ?? 'Generating…') : `Generate ${total} output${total === 1 ? '' : 's'}`}
        </button>
        {busy && (
          <div className="h-1.5 w-40 overflow-hidden rounded-full bg-ink-200">
            <div
              className="h-full rounded-full bg-brand-600 transition-all"
              style={{ width: `${Math.max((job?.progress ?? 0) * 100, 5)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{label}</p>
      {children}
    </div>
  )
}
