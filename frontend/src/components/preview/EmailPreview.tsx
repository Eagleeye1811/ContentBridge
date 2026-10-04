import { useState } from 'react'
import { api, ApiError } from '@/api/client'
import { Block } from '@/components/preview/blocks'
import { Button, Notice } from '@/components/ui'
import { Icon } from '@/lib/icons'
import type { ContentIR, SendEmailResponse } from '@/types/api'

interface EmailPreviewProps {
  ir: ContentIR
  audience: string
  outputId?: string
  options?: Record<string, string>
}

/**
 * Enhanced Official Government & Corporate Email View.
 * Displays formal email headers, structured body, and provides direct email dispatch.
 */
export default function EmailPreview({
  ir,
  audience,
  outputId,
  options = {},
}: EmailPreviewProps) {
  const [toEmail, setToEmail] = useState('')
  const [ccEmail, setCcEmail] = useState('')
  const [note, setNote] = useState('')
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<SendEmailResponse | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const urgency = options.urgency ?? 'high'
  const purpose = options.purpose ?? 'directive'

  const urgencyBadge = {
    critical: { label: 'CRITICAL ACTION REQUIRED', color: 'bg-red-600 text-white' },
    high: { label: 'HIGH PRIORITY', color: 'bg-amber-600 text-white' },
    standard: { label: 'OFFICIAL COMMUNICATION', color: 'bg-blue-700 text-white' },
    fyi: { label: 'INFORMATIONAL / FYI', color: 'bg-ink-700 text-white' },
  }[urgency] ?? { label: 'OFFICIAL', color: 'bg-blue-700 text-white' }

  const todayStr = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  // Format full plain text for clipboard or mailto
  const plainBody = [
    `Subject: ${ir.title}`,
    `From: National Technical Research Organisation (NTRO) <alerts@contentbridge.io>`,
    `To: ${audience}`,
    `Date: ${todayStr}`,
    `Classification: OFFICIAL / SENSITIVE`,
    `---`,
    '',
    ...ir.nodes.map((n) => {
      if (n.kind === 'bullets') {
        return (n.items || []).map((item) => `• ${item}`).join('\n')
      }
      return n.text || ''
    }),
  ].join('\n')

  async function handleSend() {
    if (!outputId) {
      setSendError('Please save or select this output first.')
      return
    }
    if (!toEmail.trim() || !toEmail.includes('@')) {
      setSendError('Please enter a valid recipient email address.')
      return
    }

    setSending(true)
    setSendError(null)
    setSendResult(null)

    try {
      const ccList = ccEmail
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)

      const result = await api.sendEmail(outputId, {
        to_email: toEmail.trim(),
        cc_emails: ccList.length > 0 ? ccList : undefined,
        note: note.trim() || undefined,
      })

      setSendResult(result)
    } catch (err) {
      setSendError(err instanceof ApiError ? err.message : 'Failed to dispatch email')
    } finally {
      setSending(false)
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(plainBody)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5">
      {/* Email Viewer Card */}
      <div className="overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
        {/* Top Header / Metadata Bar */}
        <div className="border-b border-ink-200 bg-gradient-to-r from-ink-900 to-slate-900 p-6 text-white">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/10 text-white">
                <Icon name="email" className="h-4 w-4" />
              </span>
              <span className="text-xs font-semibold tracking-wider uppercase text-blue-200">
                Official Email Dispatch
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold tracking-wide uppercase ${urgencyBadge.color}`}
              >
                {urgencyBadge.label}
              </span>
              <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-medium text-ink-300">
                RESTRICTED
              </span>
            </div>
          </div>

          <h2 className="mt-4 text-xl font-bold tracking-tight text-white">{ir.title}</h2>

          <div className="mt-4 grid gap-2 rounded-xl bg-white/5 p-3.5 text-xs text-ink-200 sm:grid-cols-2">
            <div>
              <span className="font-semibold text-ink-400">From: </span>
              <span className="text-white">
                Cybersecurity Directorate · NTRO{' '}
                <span className="text-ink-400">&lt;alerts@contentbridge.io&gt;</span>
              </span>
            </div>
            <div>
              <span className="font-semibold text-ink-400">To: </span>
              <span className="text-white">{audience}</span>
            </div>
            <div>
              <span className="font-semibold text-ink-400">Date: </span>
              <span>{todayStr}</span>
            </div>
            <div>
              <span className="font-semibold text-ink-400">Purpose: </span>
              <span className="capitalize">{purpose.replace('_', ' ')}</span>
            </div>
          </div>
        </div>

        {/* Email Body Content */}
        <div className="divide-y divide-ink-100 px-6 py-6 sm:px-8">
          <div className="space-y-4 text-ink-900 leading-relaxed">
            {ir.nodes.map((node) => (
              <Block key={node.id} node={node} />
            ))}
          </div>
        </div>

        {/* Quick Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-100 bg-ink-50 px-6 py-3">
          <p className="text-xs text-ink-500">
            Certified Source Traceable · All citations anchored to source document
          </p>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={handleCopy}>
              <Icon name="text" />
              {copied ? 'Copied to clipboard!' : 'Copy full email'}
            </Button>
          </div>
        </div>
      </div>

      {/* Direct Email Dispatch Panel */}
      <div className="rounded-2xl border border-blue-100 bg-gradient-to-b from-blue-50/60 to-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Icon name="email" className="h-5 w-5" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-ink-900">Send This Official Email</h3>
            <p className="text-xs text-ink-600">
              Transmit this formatted email directly to designated recipients with audit logging.
            </p>
          </div>
        </div>

        {sendError && (
          <div className="mt-4">
            <Notice tone="bad">{sendError}</Notice>
          </div>
        )}

        {sendResult && (
          <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-900">
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white text-xs">
                ✓
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-sm">Email successfully dispatched!</p>
                <p className="mt-1 text-xs text-emerald-800">{sendResult.detail}</p>
                <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-emerald-700">
                  <span>
                    <strong>Message ID:</strong> {sendResult.message_id}
                  </span>
                  <span>
                    <strong>Mode:</strong> {sendResult.delivery_mode.toUpperCase()}
                  </span>
                  <span>
                    <strong>Timestamp:</strong> {new Date(sendResult.sent_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700">
              Recipient Email Address <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={toEmail}
              onChange={(e) => setToEmail(e.target.value)}
              placeholder="e.g. director.cyber@ntro.gov.in"
              className="mt-1.5 w-full rounded-xl border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700">
              CC Email(s) <span className="text-ink-400 font-normal">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={ccEmail}
              onChange={(e) => setCcEmail(e.target.value)}
              placeholder="e.g. soc-leads@ntro.gov.in, ciso@gov.in"
              className="mt-1.5 w-full rounded-xl border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>

          <div className="sm:col-span-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-700">
              Optional Note / Transmission Header
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. High-priority incident notification regarding recent infrastructure telemetry."
              className="mt-1.5 w-full rounded-xl border border-ink-200 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
            />
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between gap-3 pt-2">
          <p className="text-xs text-ink-500">
            Logged into immutable security audit trail upon dispatch.
          </p>
          <Button onClick={handleSend} disabled={sending || !toEmail.trim()}>
            <Icon name="email" />
            {sending ? 'Dispatching Email…' : 'Send Official Email'}
          </Button>
        </div>
      </div>
    </div>
  )
}
