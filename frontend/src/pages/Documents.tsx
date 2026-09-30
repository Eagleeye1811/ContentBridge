import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { HealthResponse } from '@/types/api'

export default function Documents() {
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Documents</h2>
        <p className="text-sm text-ink-600">
          Upload an authoritative document to begin. Parsing and fact extraction land in Phase 1–2.
        </p>
      </div>

      <div className="rounded-xl border border-dashed border-ink-200 bg-white p-12 text-center">
        <p className="text-sm text-ink-600">No documents yet.</p>
        <button
          disabled
          className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white opacity-50"
        >
          Upload document (Phase 1)
        </button>
      </div>

      <div className="rounded-xl border border-ink-200 bg-white p-4">
        <h3 className="text-sm font-semibold">System</h3>
        <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
          {health ? (
            <>
              <Stat label="API" value={health.status} />
              <Stat label="Database" value={health.database ? 'connected' : 'down'} />
              <Stat label="LLM" value={health.llm_provider} />
              <Stat label="Embeddings" value={health.embedding_provider} />
            </>
          ) : (
            <span className="text-ink-400">unreachable</span>
          )}
        </dl>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-400">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}
