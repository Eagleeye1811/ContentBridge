import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import type { Claim, VerdictKind, VerificationSummary } from '@/types/api'

export const VERDICT_TONE: Record<VerdictKind, string> = {
  supported: 'bg-emerald-100 text-emerald-700',
  partial: 'bg-amber-100 text-amber-700',
  unsupported: 'bg-ink-200 text-ink-600',
  contradicted: 'bg-red-100 text-red-700',
}

interface Props {
  outputId: string
  onVerified: () => void
  onFocusNode: (nodeId: string) => void
}

export default function VerificationPanel({ outputId, onVerified, onFocusNode }: Props) {
  const [summary, setSummary] = useState<VerificationSummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.getClaims(outputId).then(setSummary).catch(() => setSummary(null))
  }, [outputId])

  useEffect(load, [load])

  async function verify() {
    setBusy(true)
    setError(null)
    try {
      const job = await api.verifyOutput(outputId)
      const final = await api.streamJob(job.id, () => {})
      if (final.status === 'failed') {
        setError(final.error ?? 'Verification failed')
        return
      }
      load()
      onVerified()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed')
    } finally {
      setBusy(false)
    }
  }

  const score = summary?.trust_score
  const verified = summary && summary.claims.length > 0

  return (
    <div className="rounded-xl border border-ink-200 bg-white p-3">
      <div className="flex items-center gap-2">
        <p className="text-sm font-semibold">Verification</p>
        {verified && score !== null && score !== undefined && (
          <span
            className={`rounded px-1.5 py-0.5 text-xs font-semibold ${
              score >= 0.85
                ? 'bg-emerald-100 text-emerald-700'
                : score >= 0.6
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-red-100 text-red-700'
            }`}
          >
            trust {Math.round(score * 100)}%
          </span>
        )}
        <button
          onClick={verify}
          disabled={busy}
          className="ml-auto rounded-lg border border-ink-200 px-2.5 py-1 text-xs font-medium hover:border-ink-400 disabled:opacity-50"
        >
          {busy ? 'Verifying…' : verified ? 'Re-verify' : 'Verify'}
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-red-700">{error}</p>}

      {!verified ? (
        <p className="mt-2 text-xs text-ink-600">
          Claims are adjudicated against the blocks they cite, with retrieval as a fallback so an
          uncited claim still gets a hearing.
        </p>
      ) : (
        <>
          <div className="mt-2 flex flex-wrap gap-1">
            {(Object.entries(summary.counts) as [VerdictKind, number][]).map(([verdict, n]) => (
              <span
                key={verdict}
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                  VERDICT_TONE[verdict] ?? 'bg-ink-200 text-ink-600'
                }`}
              >
                {n} {verdict}
              </span>
            ))}
          </div>

          {summary.blocking_reasons.length > 0 && (
            <div className="mt-2 rounded-lg bg-red-50 px-2 py-1.5">
              <p className="text-xs font-medium text-red-700">Cannot be approved yet</p>
              <ul className="mt-0.5 list-disc pl-4 text-xs text-red-700">
                {summary.blocking_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          <ul className="mt-2 max-h-80 space-y-1 overflow-y-auto">
            {[...summary.claims]
              .sort((a, b) => rank(a) - rank(b))
              .map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => onFocusNode(c.node_id)}
                    className="block w-full rounded-lg border border-ink-200 p-2 text-left hover:border-ink-400"
                  >
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                          VERDICT_TONE[c.verdict ?? 'unsupported']
                        }`}
                      >
                        {c.verdict}
                      </span>
                      {c.evidence[0] && (
                        <span className="text-xs text-ink-400">p{c.evidence[0].page_no}</span>
                      )}
                    </div>
                    <p className="mt-1 text-xs">{c.text}</p>
                    {c.rationale && (
                      <p className="mt-0.5 text-xs italic text-ink-400">{c.rationale}</p>
                    )}
                  </button>
                </li>
              ))}
          </ul>
        </>
      )}
    </div>
  )
}

/** Worst verdicts first: a reviewer should see problems before confirmations. */
function rank(c: Claim): number {
  return { contradicted: 0, unsupported: 1, partial: 2, supported: 3 }[c.verdict ?? 'unsupported']
}
