import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '@/api/client'
import { friendlyStage } from '@/components/AddSource'
import { Button, Field, Progress, Segmented, Select } from '@/components/ui'
import { Icon } from '@/lib/icons'
import { languageLabel } from '@/lib/labels'
import type { Doc, FormatInfo, Job } from '@/types/api'

interface Props {
  format: FormatInfo
  sources: Doc[]
  languages: string[]
  initialSource?: string
  onCreated: (outputIds: string[]) => void
  onCancel?: () => void
}

function defaultOptions(format: FormatInfo): Record<string, string> {
  return Object.fromEntries(format.options.map((o) => [o.key, o.default]))
}

/**
 * Create one output: pick a source, this output's own options and a
 * language. Tone and style are chosen automatically to suit the output.
 */
export default function CreateForm({
  format,
  sources,
  languages,
  initialSource,
  onCreated,
  onCancel,
}: Props) {
  const ready = sources.filter((d) => d.status === 'ready')
  const [source, setSource] = useState(
    initialSource && ready.some((d) => d.id === initialSource) ? initialSource : (ready[0]?.id ?? ''),
  )
  const [options, setOptions] = useState(() => defaultOptions(format))
  const [language, setLanguage] = useState('en')
  const [job, setJob] = useState<Job | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setOptions(defaultOptions(format))
    setError(null)
  }, [format])

  async function create() {
    setRunning(true)
    setError(null)
    try {
      const started = await api.generate(source, {
        types: [format.key],
        languages: [language],
        options: { [format.key]: options },
      })
      setJob(started)
      const final = await api.streamJob(started.id, setJob)
      if (final.status === 'failed') {
        setError(final.error ?? 'Something went wrong while writing.')
        return
      }
      onCreated(final.result?.outputs ?? [])
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong while writing.')
    } finally {
      setRunning(false)
      setJob(null)
    }
  }

  const name = format.name.toLowerCase()

  if (ready.length === 0) {
    return (
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-dashed border-ink-200 bg-white p-6">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-100 text-ink-400">
          <Icon name="document" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-medium">Add a source first</p>
          <p className="text-sm text-ink-600">
            A {name} is written from the key facts of a document, image or text.
          </p>
        </div>
        <Link to="/sources">
          <Button>
            <Icon name="plus" />
            Add a source
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-ink-200 bg-white shadow-sm">
      <div className="flex items-center gap-3 border-b border-ink-100 px-5 py-4">
        <p className="font-semibold">New {name}</p>
        <p className="hidden text-sm text-ink-400 sm:block">
          Written only from the facts in your source
        </p>
        {onCancel && !running && (
          <button
            onClick={onCancel}
            className="ml-auto rounded-lg px-2 py-1 text-sm text-ink-400 hover:bg-ink-100 hover:text-ink-900"
          >
            Close
          </button>
        )}
      </div>

      <div className="grid gap-x-8 gap-y-5 px-5 py-5 md:grid-cols-2 xl:grid-cols-[minmax(0,1.3fr)_repeat(3,auto)]">
        <Field label="From source">
          <Select
            value={source}
            onChange={setSource}
            options={ready.map((d) => ({ key: d.id, label: d.filename }))}
          />
        </Field>
        {format.options.map((o) => (
          <Field key={o.key} label={o.label}>
            <Segmented
              options={o.choices}
              value={options[o.key] ?? o.default}
              onChange={(v) => setOptions((cur) => ({ ...cur, [o.key]: v }))}
            />
          </Field>
        ))}
        <Field label="Language">
          <Segmented
            options={languages.map((code) => ({ key: code, label: languageLabel(code) }))}
            value={language}
            onChange={setLanguage}
          />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-b-2xl border-t border-ink-100 bg-ink-50 px-5 py-3">
        {running ? (
          <div className="min-w-48 flex-1">
            <Progress value={job?.progress ?? 0.05} label={friendlyStage(job?.stage ?? 'generating')} />
          </div>
        ) : error ? (
          <p className="flex-1 text-sm text-red-700">{error}</p>
        ) : (
          <p className="flex-1 text-xs text-ink-400">Usually ready in under a minute.</p>
        )}
        <Button onClick={create} disabled={running || !source}>
          <Icon name="spark" />
          {running ? 'Creating…' : `Create ${name}`}
        </Button>
      </div>
    </div>
  )
}
