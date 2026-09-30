import { useState } from 'react'
import { api } from '@/api/client'

const EXTENSION: Record<string, string> = {
  markdown: 'md',
  text: 'txt',
  html: 'html',
  docx: 'docx',
  pptx: 'pptx',
}

const LABEL: Record<string, string> = {
  markdown: 'Markdown',
  text: 'Text',
  html: 'HTML',
  docx: 'Word',
  pptx: 'PowerPoint',
}

interface Props {
  outputId: string
  filenameStem: string
  renderers: string[]
  onError: (message: string) => void
}

export default function ExportBar({ outputId, filenameStem, renderers, onError }: Props) {
  const [citations, setCitations] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)

  async function download(format: string) {
    setBusy(format)
    try {
      const url = await api.exportUrl(outputId, format, citations)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filenameStem}.${EXTENSION[format] ?? format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <label className="flex items-center gap-1 text-xs text-ink-600">
        <input
          type="checkbox"
          checked={citations}
          onChange={(e) => setCitations(e.target.checked)}
          className="accent-brand-600"
        />
        sources
      </label>
      {renderers.map((format) => (
        <button
          key={format}
          onClick={() => download(format)}
          disabled={busy !== null}
          className="rounded-lg border border-ink-200 px-2.5 py-1.5 text-xs font-medium hover:border-ink-400 disabled:opacity-50"
        >
          {busy === format ? '…' : (LABEL[format] ?? format)}
        </button>
      ))}
    </div>
  )
}
