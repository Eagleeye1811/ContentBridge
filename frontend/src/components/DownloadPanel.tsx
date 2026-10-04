import { useState } from 'react'
import { api } from '@/api/client'
import { Icon } from '@/lib/icons'

const FILES: Record<string, { label: string; ext: string; note: string }> = {
  mp4: { label: 'MP4 Video', ext: 'mp4', note: 'Rendered video with audio narration' },
  pptx: { label: 'PowerPoint', ext: 'pptx', note: 'Ready-to-present slides' },
  docx: { label: 'Word', ext: 'docx', note: 'Edit in Word or Google Docs' },
  srt: { label: 'Subtitles', ext: 'srt', note: 'For your video editor' },
  text: { label: 'Plain text', ext: 'txt', note: 'Copy and paste anywhere' },
  html: { label: 'Web page', ext: 'html', note: 'Open in any browser' },
  markdown: { label: 'Markdown', ext: 'md', note: 'For websites and wikis' },
}

/** Download buttons, most useful format first. */
export default function DownloadPanel({
  outputId,
  filenameStem,
  renderers,
  onError,
}: {
  outputId: string
  filenameStem: string
  renderers: string[]
  onError: (message: string) => void
}) {
  const [busy, setBusy] = useState<string | null>(null)
  const order = Object.keys(FILES)
  const sorted = [...renderers].sort((a, b) => order.indexOf(a) - order.indexOf(b))

  async function download(format: string) {
    setBusy(format)
    try {
      const url = await api.exportUrl(outputId, format, false)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filenameStem}.${FILES[format]?.ext ?? format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Download failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-2">
      {sorted.map((format, i) => {
        const file = FILES[format] ?? { label: format, ext: format, note: '' }
        const primary = i === 0
        return (
          <button
            key={format}
            onClick={() => download(format)}
            disabled={busy !== null}
            className={`flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-left transition disabled:opacity-50 ${
              primary
                ? 'bg-brand-600 text-white hover:bg-brand-500'
                : 'border border-ink-200 bg-white hover:border-ink-400'
            }`}
          >
            <Icon name="download" className={`h-4 w-4 ${primary ? 'text-blue-100' : 'text-ink-400'}`} />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium">{file.label}</span>
              {file.note && (
                <span className={`block text-xs ${primary ? 'text-blue-100' : 'text-ink-400'}`}>
                  {file.note}
                </span>
              )}
            </span>
            {busy === format && <span className="text-xs">Preparing…</span>}
          </button>
        )
      })}
    </div>
  )
}
