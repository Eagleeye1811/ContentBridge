import { Block, Paper } from '@/components/preview/blocks'
import type { ContentIR } from '@/types/api'

/** A press release laid out the way newsrooms expect it. */
export default function PressReleasePreview({ ir }: { ir: ContentIR }) {
  // The first level-1 heading is the headline; fall back to the title.
  const headline = ir.nodes.find((n) => n.kind === 'heading' && (n.level ?? 1) <= 1)
  const body = ir.nodes.filter((n) => n !== headline)
  return (
    <Paper>
      <p className="text-xs font-bold uppercase tracking-widest text-ink-600">
        For immediate release
      </p>
      <h1 className="mt-4 text-2xl font-bold leading-tight tracking-tight">
        {headline?.text ?? headline?.title ?? ir.title}
      </h1>
      <div className="mt-4">
        {body.map((node, i) =>
          i === 0 && node.kind === 'paragraph' ? (
            <p key={node.id} className="mt-3 text-[15px] font-medium leading-relaxed">
              {node.text}
            </p>
          ) : (
            <Block key={node.id} node={node} />
          ),
        )}
      </div>
      <p className="mt-8 text-center text-sm tracking-[0.5em] text-ink-400">###</p>
    </Paper>
  )
}
