import { useState } from 'react'
import { api } from '@/api/client'
import { Icon } from '@/lib/icons'

interface FormatConfig {
  label: string
  ext: string
  note: string
  badge: string
  badgeColor: string
  icon: 'download' | 'report' | 'presentation'
  iconBg: string
}

const FILES: Record<string, FormatConfig> = {
  html: {
    label: 'Web Page & PDF',
    ext: 'html',
    note: 'Interactive view & 1-click Print to PDF',
    badge: 'HTML / PDF',
    badgeColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    icon: 'download',
    iconBg: 'bg-emerald-50 text-emerald-600 border-emerald-200 group-hover:bg-emerald-600 group-hover:text-white',
  },
  docx: {
    label: 'Microsoft Word',
    ext: 'docx',
    note: 'Editable formatted report (.docx)',
    badge: 'DOCX',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    icon: 'report',
    iconBg: 'bg-blue-50 text-blue-600 border-blue-200 group-hover:bg-blue-600 group-hover:text-white',
  },
  pptx: {
    label: 'PowerPoint Deck',
    ext: 'pptx',
    note: 'Formatted presentation slides',
    badge: 'PPTX',
    badgeColor: 'bg-orange-50 text-orange-700 border-orange-200',
    icon: 'presentation',
    iconBg: 'bg-orange-50 text-orange-600 border-orange-200 group-hover:bg-orange-600 group-hover:text-white',
  },
  text: {
    label: 'Plain Text',
    ext: 'txt',
    note: 'Universal copy-paste text',
    badge: 'TXT',
    badgeColor: 'bg-ink-100 text-ink-700 border-ink-200',
    icon: 'download',
    iconBg: 'bg-ink-50 text-ink-600 border-ink-200 group-hover:bg-ink-800 group-hover:text-white',
  },
  markdown: {
    label: 'Markdown',
    ext: 'md',
    note: 'For documentation and wikis',
    badge: 'MD',
    badgeColor: 'bg-purple-50 text-purple-700 border-purple-200',
    icon: 'download',
    iconBg: 'bg-purple-50 text-purple-600 border-purple-200 group-hover:bg-purple-600 group-hover:text-white',
  },
  srt: {
    label: 'Subtitles Track',
    ext: 'srt',
    note: 'Video production timestamps',
    badge: 'SRT',
    badgeColor: 'bg-amber-50 text-amber-700 border-amber-200',
    icon: 'download',
    iconBg: 'bg-amber-50 text-amber-600 border-amber-200 group-hover:bg-amber-600 group-hover:text-white',
  },
}

/**
 * Senior-engineered, robust Download & Export Panel.
 * Zero-overlap flex layout designed for narrow sidebars.
 */
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
  const order = ['html', 'docx', 'pptx', 'text', 'markdown', 'srt']
  const sorted = [...renderers].sort((a, b) => order.indexOf(a) - order.indexOf(b))

  async function handleExport(format: string) {
    setBusy(format)
    try {
      const url = await api.exportUrl(outputId, format, false)
      if (format === 'html') {
        // Open web page in new tab for instant interactive view & 1-click PDF printing
        window.open(url, '_blank')
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = `${filenameStem}.${FILES[format]?.ext ?? format}`
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Export failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-2">
      {sorted.map((format) => {
        const file = FILES[format] ?? {
          label: format.toUpperCase(),
          ext: format,
          note: 'Export document',
          badge: format.toUpperCase(),
          badgeColor: 'bg-ink-100 text-ink-700 border-ink-200',
          icon: 'download',
          iconBg: 'bg-ink-50 text-ink-600 border-ink-200 group-hover:bg-ink-800 group-hover:text-white',
        }
        const isBusy = busy === format
        const isHTML = format === 'html'

        return (
          <button
            key={format}
            type="button"
            onClick={() => handleExport(format)}
            disabled={busy !== null}
            className={`group relative flex w-full items-center gap-3 rounded-xl border p-2.5 text-left transition-all duration-150 active:scale-[0.99] disabled:opacity-50 cursor-pointer ${
              isHTML
                ? 'border-brand-300/80 bg-gradient-to-r from-blue-50/50 to-emerald-50/20 hover:border-brand-500 hover:bg-white hover:shadow-xs'
                : 'border-ink-200/90 bg-white hover:border-ink-400 hover:bg-ink-50/40 hover:shadow-xs'
            }`}
          >
            {/* Format Icon Container */}
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors duration-150 ${file.iconBg}`}
            >
              <Icon name={file.icon} className="h-4 w-4" />
            </div>

            {/* Label and Subtitle Area */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-1.5">
                <span className="truncate text-xs font-bold text-ink-900 group-hover:text-brand-700">
                  {file.label}
                </span>
                <span
                  className={`shrink-0 rounded px-1.5 py-0.2 text-[9px] font-bold tracking-wider uppercase border ${file.badgeColor}`}
                >
                  {file.badge}
                </span>
              </div>
              <p className="truncate text-[11px] text-ink-500 mt-0.5">
                {isBusy ? 'Generating export…' : file.note}
              </p>
            </div>

            {/* Action Arrow / Indicator */}
            <div className="shrink-0 text-ink-400 group-hover:text-brand-600 transition-colors">
              {isHTML ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  className="transition-transform group-hover:translate-x-0.5"
                >
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              ) : (
                <Icon
                  name="download"
                  className="h-3.5 w-3.5 transition-transform group-hover:translate-y-0.5"
                />
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
