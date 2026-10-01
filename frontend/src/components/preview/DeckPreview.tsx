import type { ContentIR } from '@/types/api'

/** A presentation shown as slides, laid out like the downloaded PowerPoint. */
export default function DeckPreview({ ir }: { ir: ContentIR }) {
  const slides = ir.nodes.filter((n) => n.kind === 'slide')
  const total = slides.length + 1
  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <Slide number={1} total={total}>
        <div className="flex h-full flex-col justify-center px-[8%]">
          <div className="mb-[4%] h-1 w-[18%] rounded-full bg-brand-600" />
          <h1 className="text-[clamp(1.1rem,3.2vw,2.1rem)] font-semibold leading-tight tracking-tight">
            {ir.title}
          </h1>
        </div>
      </Slide>

      {slides.map((node, index) => (
        <div key={node.id}>
          <Slide number={index + 2} total={total}>
            <div className="flex h-full flex-col px-[7%] pt-[6%]">
              <div className="mb-[3%] h-1 w-[12%] rounded-full bg-brand-600" />
              <h2 className="text-[clamp(0.95rem,2.4vw,1.6rem)] font-semibold leading-snug">
                {node.title}
              </h2>
              <ul className="mt-[4%] space-y-[2.2%] text-[clamp(0.75rem,1.7vw,1.05rem)] leading-snug text-ink-600">
                {(node.items ?? []).map((item, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-brand-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Slide>
          {node.notes && (
            <p className="mt-2 px-1 text-sm leading-relaxed text-ink-600">
              <span className="font-medium text-ink-400">Speaker notes: </span>
              {node.notes}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

function Slide({
  number,
  total,
  children,
}: {
  number: number
  total: number
  children: React.ReactNode
}) {
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
      {children}
      <span className="absolute bottom-[4%] right-[4%] text-[11px] text-ink-400">
        {number} / {total}
      </span>
    </div>
  )
}
