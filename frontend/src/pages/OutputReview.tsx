import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '@/api/client'
import ContentEditor from '@/components/ContentEditor'
import DownloadPanel from '@/components/DownloadPanel'
import OutputPreview from '@/components/preview/OutputPreview'
import { Button, Notice } from '@/components/ui'
import { typeOf } from '@/lib/formats'
import { Icon } from '@/lib/icons'
import { formatLabel, languageLabel, timeAgo } from '@/lib/labels'
import type { ContentIR, OutputDetail } from '@/types/api'

/** One created output: see it as it will look, fix it if needed, download it. */
export default function OutputReview() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [output, setOutput] = useState<OutputDetail | null>(null)
  const [sourceName, setSourceName] = useState('')
  const [draft, setDraft] = useState<ContentIR | null>(null)
  const [editing, setEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<'save' | 'rewrite' | null>(null)

  const load = useCallback(() => {
    api
      .getOutput(id)
      .then((o) => {
        setOutput(o)
        setDraft(o.content_ir)
        api
          .getDocument(o.document_id)
          .then((d) => setSourceName(d.filename))
          .catch(() => setSourceName(''))
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load'))
  }, [id])

  useEffect(load, [load])

  async function save() {
    if (!draft) return
    setBusy('save')
    setError(null)
    try {
      const updated = await api.updateOutput(id, draft)
      setOutput(updated)
      setDraft(updated.content_ir)
      setEditing(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save')
    } finally {
      setBusy(null)
    }
  }

  async function rewrite() {
    setBusy('rewrite')
    setError(null)
    try {
      const job = await api.regenerate(id)
      const final = await api.streamJob(job.id, () => { })
      if (final.status === 'failed') {
        setError(final.error ?? 'Could not write a new version')
        return
      }
      const created = final.result?.outputs?.[0]
      if (created) navigate(`/outputs/${created}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not write a new version')
    } finally {
      setBusy(null)
    }
  }

  if (error && !output)
    return (
      <div className="space-y-4">
        <Notice tone="bad">{error}</Notice>
        <Link
          to="/outputs"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:text-brand-700"
        >
          <Icon name="back" />
          Back to all outputs
        </Link>
      </div>
    )

  if (!output || !draft) return <div className="p-10 text-sm text-ink-400">Loading output…</div>

  const type = typeOf(output)
  const locked = output.status === 'approved'
  const dirty = draft !== output.content_ir

  return (
    <div className="space-y-6">
      <Link
        to={`/formats/${type}`}
        className="inline-flex items-center gap-1 text-sm text-ink-600 hover:text-ink-900"
      >
        <Icon name="back" />
        Back to {formatLabel(type)}
      </Link>

      <div className="flex flex-wrap items-center gap-4">
        <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-brand-600">
          <Icon name={type} className="h-6 w-6" />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-2xl font-semibold tracking-tight">{draft.title}</h1>
          <p className="text-sm text-ink-600">
            {formatLabel(type)} · {languageLabel(output.language)}
            {sourceName && ` · from ${sourceName}`} · {timeAgo(output.created_at)}
            {output.version > 1 && ` · version ${output.version}`}
          </p>
        </div>
      </div>

      {error && <Notice tone="bad">{error}</Notice>}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_17rem]">
        <div className="min-w-0">
          {editing ? (
            <div className="mx-auto max-w-3xl rounded-xl border border-ink-200 bg-white p-6 shadow-sm">
              <ContentEditor draft={draft} onChange={setDraft} />
            </div>
          ) : (
            <OutputPreview
              type={type}
              ir={draft}
              audience={output.audience}
              options={output.controls?.format}
              outputId={id}
            />
          )}
        </div>

        <aside className="space-y-5 lg:sticky lg:top-20 lg:self-start">
          {editing ? (
            <div className="space-y-2 rounded-2xl border border-ink-200 bg-white p-4 shadow-sm">
              <p className="font-semibold">Editing</p>
              <p className="text-xs text-ink-600">Change any text, then save.</p>
              <Button onClick={save} disabled={!dirty || busy !== null} wide>
                {busy === 'save' ? 'Saving…' : 'Save changes'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setDraft(output.content_ir)
                  setEditing(false)
                }}
                wide
              >
                Cancel
              </Button>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-ink-200 bg-white p-4 shadow-sm">
                <p className="font-semibold">Looks right?</p>
                <p className="mb-3 text-xs text-ink-600">Download it in the format you need.</p>
                <DownloadPanel
                  outputId={id}
                  filenameStem={`${type}_${output.language}_v${output.version}`}
                  renderers={output.renderers}
                  onError={setError}
                />
              </div>

              <div className="space-y-2 rounded-2xl border border-ink-200 bg-white p-4 shadow-sm">
                <p className="font-semibold">Needs changes?</p>
                <Button
                  variant="secondary"
                  onClick={() => setEditing(true)}
                  disabled={locked || busy !== null}
                  wide
                >
                  <Icon name="edit" />
                  Edit the text
                </Button>
                <Button variant="secondary" onClick={rewrite} disabled={busy !== null} wide>
                  <Icon name="spark" />
                  {busy === 'rewrite' ? 'Writing…' : 'Write a new version'}
                </Button>
              </div>
            </>
          )}
        </aside>
      </div>
    </div>
  )
}
