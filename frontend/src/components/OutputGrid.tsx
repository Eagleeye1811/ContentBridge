import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui'
import { typeOf } from '@/lib/formats'
import { Icon } from '@/lib/icons'
import { formatLabel, languageLabel, timeAgo } from '@/lib/labels'
import type { OutputListItem } from '@/types/api'

/** Created outputs as cards: easy to scan, one click to open. */
export default function OutputGrid({
  outputs,
  highlight = [],
  showFormat = false,
}: {
  outputs: OutputListItem[]
  highlight?: string[]
  /** Name each card's output type (for lists that mix types). */
  showFormat?: boolean
}) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {outputs.map((o) => {
        const fresh = highlight.includes(o.id)
        return (
          <li key={o.id}>
            <Link
              to={`/outputs/${o.id}`}
              className={`group flex h-full flex-col rounded-2xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                fresh ? 'border-brand-500 ring-2 ring-blue-100' : 'border-ink-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-brand-600">
                  <Icon name={typeOf(o)} />
                </span>
                {fresh && <Badge tone="info">New</Badge>}
              </div>

              {showFormat && (
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-brand-600">
                  {formatLabel(typeOf(o))}
                </p>
              )}
              <p className={`${showFormat ? 'mt-1' : 'mt-4'} line-clamp-2 font-semibold leading-snug group-hover:text-brand-600`}>
                {o.title || 'Untitled'}
              </p>
              <p className="mt-1 truncate text-sm text-ink-600" title={o.document_name}>
                From {o.document_name}
              </p>

              <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-ink-100 pt-3 text-xs text-ink-400">
                <span>{languageLabel(o.language)}</span>
                <span>{timeAgo(o.created_at)}</span>
                {o.version > 1 && <span>Version {o.version}</span>}
              </div>
            </Link>
          </li>
        )
      })}
    </ul>
  )
}
