import { useCallback, useRef, useState } from 'react'
import { api } from '@/api/client'
import { Button, Card, Progress, Segmented } from '@/components/ui'
import { Icon } from '@/lib/icons'
import type { Job } from '@/types/api'

type Mode = 'file' | 'image' | 'text'

const MODES: { key: Mode; label: string }[] = [
  { key: 'file', label: 'Document' },
  { key: 'image', label: 'Image' },
  { key: 'text', label: 'Paste text' },
]

const ACCEPT: Record<Exclude<Mode, 'text'>, string> = {
  file: '.pdf,.docx,.pptx,.txt,.md',
  image: '.png,.jpg,.jpeg',
}

const HINT: Record<Exclude<Mode, 'text'>, string> = {
  file: 'PDF, Word, PowerPoint or text file, up to 50 MB',
  image: 'A photo or scan of a notice, letter or page (PNG or JPG)',
}

const MIN_TEXT_CHARS = 40

/** Every kind of source is uploaded the same way and read into key facts. */
export default function AddSource({ onComplete }: { onComplete: (documentId: string) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<Mode>('file')
  const [dragging, setDragging] = useState(false)
  const [job, setJob] = useState<Job | null>(null)
  const [uploading, setUploading] = useState(false)
  const [filename, setFilename] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')

  const upload = useCallback(
    async (file: File) => {
      setError(null)
      setFilename(file.name)
      setUploading(true)
      try {
        const { document, job: started } = await api.uploadDocument(file)
        setJob(started)
        const final = await api.streamJob(started.id, setJob)
        if (final.status === 'failed') {
          setError(final.error ?? 'We could not read this source.')
          return
        }
        setTitle('')
        setText('')
        onComplete(document.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setJob(null)
        setUploading(false)
      }
    },
    [onComplete],
  )

  function submitText() {
    const stem =
      title
        .trim()
        .replace(/[^\p{L}\p{N}]+/gu, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 60) || 'pasted_text'
    const body = title.trim() ? `${title.trim()}\n\n${text.trim()}\n` : `${text.trim()}\n`
    void upload(new File([body], `${stem}.txt`, { type: 'text/plain' }))
  }

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-semibold">Add a source</p>
          <p className="text-sm text-ink-600">
            We read it and pull out the key facts. Everything you create is based only on them.
          </p>
        </div>
        <Segmented options={MODES} value={mode} onChange={(m) => setMode(m as Mode)} />
      </div>

      {uploading ? (
        <div className="rounded-xl border border-ink-200 bg-ink-50 p-6">
          <p className="mb-3 truncate text-sm font-medium">{filename}</p>
          <Progress
            value={job?.progress ?? 0}
            label={job ? friendlyStage(job.stage) : 'Uploading…'}
          />
        </div>
      ) : mode === 'text' ? (
        <div className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title (optional)"
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={7}
            placeholder="Paste your text here. Leave a blank line between paragraphs."
            className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm leading-relaxed outline-none focus:border-brand-500"
          />
          <div className="flex items-center gap-3">
            <Button onClick={submitText} disabled={text.trim().length < MIN_TEXT_CHARS}>
              <Icon name="upload" />
              Add text
            </Button>
            {text.trim().length > 0 && text.trim().length < MIN_TEXT_CHARS && (
              <span className="text-xs text-ink-400">Add a little more text to continue</span>
            )}
          </div>
        </div>
      ) : (
        <button
          type="button"
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            const file = e.dataTransfer.files[0]
            if (file) void upload(file)
          }}
          onClick={() => inputRef.current?.click()}
          className={`flex w-full flex-col items-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
            dragging ? 'border-brand-500 bg-blue-50' : 'border-ink-200 hover:border-ink-400'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT[mode]}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) void upload(file)
              e.target.value = ''
            }}
          />
          <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-blue-50 text-brand-600">
            <Icon name={mode === 'image' ? 'image' : 'upload'} className="h-5 w-5" />
          </span>
          <span className="text-sm font-medium">
            Drop {mode === 'image' ? 'an image' : 'a file'} here, or click to choose
          </span>
          <span className="mt-1 text-xs text-ink-400">{HINT[mode]}</span>
        </button>
      )}

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </Card>
  )
}

export function friendlyStage(stage: string): string {
  if (stage.startsWith('parsing')) return 'Reading the source…'
  if (stage.startsWith('indexing')) return 'Organising the content…'
  if (stage.startsWith('extracting')) return 'Finding the key facts…'
  if (stage.startsWith('generating')) return 'Writing…'
  if (stage.startsWith('verifying') || stage.startsWith('checking')) return 'Checking accuracy…'
  if (stage === 'done') return 'Done'
  return 'Working…'
}
