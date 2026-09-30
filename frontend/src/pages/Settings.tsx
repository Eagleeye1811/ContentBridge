import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { useAuth } from '@/lib/auth'
import type { Catalog, HealthResponse } from '@/types/api'

export default function Settings() {
  const { user } = useAuth()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
    api.catalog().then(setCatalog).catch(() => setCatalog(null))
  }, [])

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h2 className="text-lg font-semibold">Settings</h2>
        <p className="text-sm text-ink-600">
          Providers are configured by environment variable, so a deployment can be repointed
          without a code change.
        </p>
      </div>

      <Card title="Signed in as">
        <Row label="Name" value={user?.name ?? '—'} />
        <Row label="Email" value={user?.email ?? '—'} />
        <Row label="Role" value={user?.role ?? '—'} />
      </Card>

      <Card title="System">
        <Row label="API" value={health?.status ?? 'unreachable'} />
        <Row label="Database" value={health?.database ? 'connected' : 'down'} />
        <Row label="Environment" value={health?.env ?? '—'} />
        <Row label="LLM provider" value={health?.llm_provider ?? '—'} />
        <Row label="Embeddings" value={health?.embedding_provider ?? '—'} />
      </Card>

      {catalog && (
        <Card title="Available outputs">
          <p className="text-sm text-ink-600">
            {catalog.formats.length} output types × {catalog.audiences.length} audiences ×{' '}
            {Object.keys(catalog.languages).length} languages, all produced by one generator.
          </p>
          <div className="mt-2 space-y-1.5">
            {catalog.formats.map((f) => (
              <div key={f.key} className="flex items-baseline gap-2 text-sm">
                <span className="w-32 shrink-0 font-medium">{f.name}</span>
                <span className="text-xs text-ink-400">{f.renderers.join(', ')}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {health?.llm_provider === 'stub' && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="font-medium">Running on the development stub</p>
          <p className="mt-0.5 text-xs">
            The stub echoes facts rather than writing. Set <code>GEMINI_API_KEY</code> and
            <code> LLM_PROVIDER=gemini</code> for real generation. Everything else — traceability,
            consistency checking, export — behaves identically either way.
          </p>
        </div>
      )}
    </div>
  )
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-ink-200 bg-white p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-2 space-y-1">{children}</div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-3 text-sm">
      <span className="w-32 shrink-0 text-ink-400">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
