import type { ContentIR } from '@/types/api'

const SHAPE: Record<string, { frame: string; grid: string }> = {
  poster: { frame: 'max-w-md', grid: 'grid-cols-1' },
  square: { frame: 'max-w-2xl', grid: 'grid-cols-2' },
  wide: { frame: 'max-w-4xl', grid: 'grid-cols-2 lg:grid-cols-3' },
}

/**
 * The infographic as a designer would start it: headline, one block per
 * section with its key number, and the suggested visual for each.
 */
export default function InfographicPreview({ ir, shape }: { ir: ContentIR; shape?: string }) {
  const s = SHAPE[shape ?? 'poster'] ?? SHAPE.poster
  const heading = ir.nodes.find((n) => n.kind === 'heading')
  const panels = ir.nodes.filter((n) => n.kind === 'panel')
  const callouts = ir.nodes.filter((n) => n.kind === 'callout')

  return (
    <div className={`mx-auto w-full ${s.frame}`}>
      <div className="flex h-full flex-col overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
        <div className="bg-brand-600 px-6 py-6 text-white">
          <p className="text-xs font-semibold uppercase tracking-widest text-blue-100">
            Infographic
          </p>
          <h1 className="mt-1 text-xl font-bold leading-tight">
            {heading?.text ?? heading?.title ?? ir.title}
          </h1>
        </div>

        <div className={`grid flex-1 gap-3 bg-ink-50 p-4 ${s.grid}`}>
          {panels.map((p, i) => (
            <div key={p.id} className="rounded-lg bg-white p-4 shadow-sm">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-xs font-bold text-brand-600">
                  {i + 1}
                </span>
                <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                  {p.title}
                </p>
              </div>
              {(p.items ?? []).map((item, j) => (
                <p key={j} className="mt-2 text-lg font-bold leading-snug">
                  {item}
                </p>
              ))}
              {p.text && <p className="mt-1 text-sm text-ink-600">{p.text}</p>}
              {p.notes && (
                <p className="mt-3 rounded-md bg-ink-50 px-2.5 py-1.5 text-xs text-ink-600">
                  <span className="font-medium">Design idea:</span> {p.notes}
                </p>
              )}
            </div>
          ))}
        </div>

        {callouts.map((c) => (
          <div key={c.id} className="bg-ink-900 px-6 py-4 text-white">
            {c.title && (
              <p className="text-xs font-semibold uppercase tracking-widest text-ink-400">
                {c.title}
              </p>
            )}
            <p className="mt-0.5 font-medium">{c.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
