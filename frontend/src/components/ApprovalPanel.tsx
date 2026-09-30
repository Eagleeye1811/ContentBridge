import { useCallback, useEffect, useState } from 'react'
import { api, ApiError } from '@/api/client'
import { useAuth } from '@/lib/auth'
import type { ApprovalState } from '@/types/api'

const ACTION_TONE: Record<string, string> = {
  approve: 'text-emerald-700',
  reject: 'text-red-700',
  comment: 'text-ink-600',
  edit: 'text-ink-600',
}

export default function ApprovalPanel({
  outputId,
  onChanged,
}: {
  outputId: string
  onChanged: () => void
}) {
  const { user } = useAuth()
  const [state, setState] = useState<ApprovalState | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.approvalState(outputId).then(setState).catch(() => setState(null))
  }, [outputId])

  useEffect(load, [load])

  async function act(fn: () => Promise<ApprovalState>) {
    setBusy(true)
    setError(null)
    try {
      setState(await fn())
      setNote('')
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }

  if (!state) return null

  const needsNote = state.can_reject && note.trim().length < 3

  return (
    <div className="rounded-xl border border-ink-200 bg-white p-3">
      <div className="flex items-center gap-2">
        <p className="text-sm font-semibold">Approval</p>
        <span className="rounded bg-ink-200 px-1.5 py-0.5 text-xs font-medium text-ink-600">
          {state.status}
        </span>
        {state.approved_at && (
          <span className="text-xs text-emerald-700">
            by {state.approver_name} · {new Date(state.approved_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {state.blocking_reasons.length > 0 && (
        <div className="mt-2 rounded-lg bg-red-50 px-2 py-1.5">
          <p className="text-xs font-medium text-red-700">Blocked from approval</p>
          <ul className="mt-0.5 list-disc pl-4 text-xs text-red-700">
            {state.blocking_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {(state.can_submit || state.can_approve || state.can_reject) && (
        <>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            placeholder={state.can_reject ? 'Reason (required to reject)' : 'Note (optional)'}
            className="mt-2 w-full rounded-lg border border-ink-200 px-2 py-1.5 text-sm outline-none focus:border-brand-500"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            {state.can_submit && (
              <button
                onClick={() => act(() => api.submitForReview(outputId, note || undefined))}
                disabled={busy}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-500 disabled:opacity-50"
              >
                Submit for review
              </button>
            )}
            {state.can_approve && (
              <button
                onClick={() => act(() => api.approveOutput(outputId, note || undefined))}
                disabled={busy}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                Approve
              </button>
            )}
            {state.can_reject && (
              <button
                onClick={() => act(() => api.rejectOutput(outputId, note))}
                disabled={busy || needsNote}
                title={needsNote ? 'A rejection needs a reason the editor can act on' : undefined}
                className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                Reject
              </button>
            )}
          </div>
        </>
      )}

      {!state.can_submit && !state.can_approve && !state.can_reject && (
        <p className="mt-2 text-xs text-ink-600">
          {state.status === 'approved'
            ? 'Approved and locked. Regenerate to make a new version.'
            : user?.role === 'editor' && state.status === 'in_review'
              ? 'Waiting on an approver.'
              : 'No action available to you at this stage.'}
        </p>
      )}

      {error && <p className="mt-2 text-xs text-red-700">{error}</p>}

      {state.history.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-t border-ink-200 pt-2">
          {state.history.map((h) => (
            <li key={h.id} className="text-xs">
              <span className={`font-medium ${ACTION_TONE[h.action] ?? ''}`}>{h.action}</span>
              <span className="text-ink-600">
                {' '}
                — {h.actor_name || 'someone'}
                {h.actor_role ? ` (${h.actor_role})` : ''} ·{' '}
                {new Date(h.created_at).toLocaleString()}
              </span>
              {h.note && <p className="mt-0.5 text-ink-600">{h.note}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
