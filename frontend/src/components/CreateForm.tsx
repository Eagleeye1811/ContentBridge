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
 * Clean, modern configuration form for generating format-specific outputs.
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
      <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-dashed border-ink-200 bg-white p-6 shadow-sm">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-brand-600">
          <Icon name="document" className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink-900">Add a source document first</p>
          <p className="text-sm text-ink-600">
            A {name} is created directly from the extracted facts of your uploaded source.
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
    <div className="overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-ink-100 bg-gradient-to-r from-ink-50 to-white px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-brand-600 shadow-xs">
            <Icon name={format.key} className="h-4 w-4" />
          </span>
          <div>
            <h2 className="font-semibold text-ink-900 capitalize">Configure New {format.name}</h2>
            <p className="text-xs text-ink-500">
              Verified generation anchored to your authoritative source of truth.
            </p>
          </div>
        </div>
        {onCancel && !running && (
          <button
            onClick={onCancel}
            className="rounded-lg px-2.5 py-1 text-xs font-medium text-ink-500 hover:bg-ink-100 hover:text-ink-900 transition"
          >
            Close
          </button>
        )}
      </div>

      {/* Main Parameters Section */}
      <div className="p-6 space-y-6">
        {/* Primary Row: Source & Language */}
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <Field label="Authoritative Source" help="Document to extract facts from">
            <Select
              value={source}
              onChange={setSource}
              options={ready.map((d) => ({ key: d.id, label: `📄 ${d.filename}` }))}
            />
          </Field>

          <Field label="Output Language" help="Target language for output">
            <Segmented
              options={languages.map((code) => ({ key: code, label: languageLabel(code) }))}
              value={language}
              onChange={setLanguage}
              className="w-full justify-start"
            />
          </Field>
        </div>

        {/* Dynamic Format Options Grid */}
        {format.options.length > 0 && (
          <div className="border-t border-ink-100 pt-5">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-2">
              {format.options.map((o) => (
                <Field key={o.key} label={o.label} help={o.help || undefined}>
                  <Segmented
                    options={o.choices}
                    value={options[o.key] ?? o.default}
                    onChange={(v) => setOptions((cur) => ({ ...cur, [o.key]: v }))}
                    className="w-full justify-start"
                  />
                </Field>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-ink-100 bg-ink-50/80 px-6 py-4">
        {running ? (
          <div className="min-w-64 flex-1">
            <Progress value={job?.progress ?? 0.05} label={friendlyStage(job?.stage ?? 'generating')} />
          </div>
        ) : error ? (
          <p className="flex-1 text-sm font-medium text-red-600">{error}</p>
        ) : (
          <div className="flex items-center gap-2 text-xs text-ink-500">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Ready to transform · Output generated in ~10–15 seconds
          </div>
        )}

        <Button onClick={create} disabled={running || !source} size="md">
          <Icon name="spark" />
          {running ? 'Generating Output…' : `Create ${format.name}`}
        </Button>
      </div>
    </div>
  )
}
