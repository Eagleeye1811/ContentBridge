/** Building blocks shared by the document-style previews. */
import type { IRNode } from '@/types/api'

const PRIORITY: Record<string, { label: string; tone: string }> = {
  critical: { label: 'Critical', tone: 'border-red-500 bg-red-50 text-red-900' },
  high: { label: 'High priority', tone: 'border-orange-500 bg-orange-50 text-orange-900' },
  medium: { label: 'Medium priority', tone: 'border-amber-500 bg-amber-50 text-amber-900' },
  low: { label: 'Low priority', tone: 'border-blue-500 bg-blue-50 text-blue-900' },
  info: { label: 'For your information', tone: 'border-blue-500 bg-blue-50 text-blue-900' },
}

/** A sheet of paper, for anything that is read like a document. */
export function Paper({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-3xl rounded-xl border border-ink-200 bg-white px-8 py-10 shadow-sm sm:px-12">
      {children}
    </div>
  )
}

export function Block({ node }: { node: IRNode }) {
  switch (node.kind) {
    case 'heading': {
      const level = node.level ?? 2
      const text = node.text ?? node.title
      if (level <= 1) return <h2 className="mt-8 text-lg font-semibold first:mt-0">{text}</h2>
      return <h3 className="mt-6 text-base font-semibold text-ink-900 first:mt-0">{text}</h3>
    }
    case 'paragraph':
      return <p className="mt-3 text-[15px] leading-relaxed text-ink-900">{node.text}</p>
    case 'quote':
      return (
        <blockquote className="mt-4 border-l-4 border-brand-600 pl-4 text-[15px] italic leading-relaxed text-ink-600">
          {node.text}
        </blockquote>
      )
    case 'bullets':
    case 'post':
      return (
        <div className="mt-3">
          {node.title && <p className="mb-1 text-sm font-semibold">{node.title}</p>}
          <ul className="list-disc space-y-1.5 pl-5 text-[15px] leading-relaxed">
            {(node.items ?? []).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )
    case 'callout': {
      const p = PRIORITY[node.severity ?? 'info'] ?? PRIORITY.info
      return (
        <div className={`mt-4 rounded-r-lg border-l-4 px-4 py-3 ${p.tone}`}>
          <p className="text-xs font-semibold uppercase tracking-wider">{node.title || p.label}</p>
          {node.text && <p className="mt-1 text-[15px] leading-relaxed">{node.text}</p>}
        </div>
      )
    }
    case 'table': {
      const [header, ...rows] = node.rows ?? []
      if (!header) return null
      return (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {header.map((cell, i) => (
                  <th key={i} className="border-b-2 border-ink-200 px-3 py-2 text-left font-semibold">
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r} className="border-b border-ink-100">
                  {row.map((cell, c) => (
                    <td key={c} className="px-3 py-2">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    default:
      return node.text ? <p className="mt-3 text-[15px] leading-relaxed">{node.text}</p> : null
  }
}
