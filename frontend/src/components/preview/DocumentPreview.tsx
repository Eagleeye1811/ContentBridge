import { Block, Paper } from '@/components/preview/blocks'
import type { ContentIR } from '@/types/api'

/** Advisory, executive summary and report: a page you read top to bottom. */
export default function DocumentPreview({ ir, kicker }: { ir: ContentIR; kicker: string }) {
  return (
    <Paper>
      <p className="text-xs font-semibold uppercase tracking-widest text-brand-600">{kicker}</p>
      <h1 className="mt-2 text-2xl font-semibold leading-tight tracking-tight">{ir.title}</h1>
      <div className="mt-6 border-t border-ink-100 pt-2">
        {ir.nodes.map((node) => (
          <Block key={node.id} node={node} />
        ))}
      </div>
    </Paper>
  )
}
