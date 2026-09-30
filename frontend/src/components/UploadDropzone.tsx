import { useCallback, useRef, useState } from 'react'
import { api } from '@/api/client'
import type { Job } from '@/types/api'

const ACCEPT = '.pdf,.docx,.pptx'

interface Props {
  onComplete: (documentId: string) => void
}

export default function UploadDropzone({ onComplete }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [job, setJob] = useState<Job | null>(null)
  const [filename, setFilename] = useState('')
  const [error, setError] = useState<string | null>(null)

  const upload = useCallback(
    async (file: File) => {
      setError(null)
      setFilename(file.name)
      setJob(null)
      try {
        const { document, job: started } = await api.uploadDocument(file)
        setJob(started)
        const final = await api.streamJob(started.id, setJob)
        if (final.status === 'failed') {
          setError(final.error ?? 'Ingestion failed')
          return
        }
        onComplete(document.id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed')
      } finally {
        setJob(null)
      }
    },
    [onComplete],
  )

  const busy = job !== null

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files[0]
          if (file && !busy) void upload(file)
        }}
        onClick={() => !busy && inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragging ? 'border-brand-500 bg-blue-50' : 'border-ink-200 bg-white hover:border-ink-400'
        } ${busy ? 'pointer-events-none opacity-60' : ''}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void upload(file)
            e.target.value = ''
          }}
        />
        {busy ? (
          <Progress job={job} filename={filename} />
        ) : (
          <>
            <p className="text-sm font-medium">Drop a document here, or click to choose</p>
            <p className="mt-1 text-xs text-ink-400">PDF, DOCX or PPTX · up to 50 MB</p>
          </>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}

function Progress({ job, filename }: { job: Job; filename: string }) {
  const pct = Math.round(job.progress * 100)
  return (
    <div className="mx-auto max-w-sm text-left">
      <div className="flex items-baseline justify-between text-sm">
        <span className="truncate font-medium">{filename}</span>
        <span className="text-ink-400">{pct}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink-200">
        <div
          className="h-full rounded-full bg-brand-600 transition-all duration-300"
          style={{ width: `${Math.max(pct, 4)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-ink-600">{job.stage || job.status}</p>
    </div>
  )
}
