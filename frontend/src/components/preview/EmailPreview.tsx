import { Block } from '@/components/preview/blocks'
import type { ContentIR } from '@/types/api'

/** An email as it would look in a mail client: subject, recipients, body. */
export default function EmailPreview({ ir, audience }: { ir: ContentIR; audience: string }) {
  return (
    <div className="mx-auto w-full max-w-3xl overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm">
      <div className="border-b border-ink-100 bg-ink-50 px-6 py-4 text-sm">
        <p className="text-lg font-semibold leading-snug">{ir.title}</p>
        <div className="mt-2 space-y-0.5 text-ink-600">
          <p>
            <span className="inline-block w-12 text-ink-400">To</span>
            {audience}
          </p>
          <p>
            <span className="inline-block w-12 text-ink-400">From</span>
            You
          </p>
        </div>
      </div>
      <div className="px-6 py-6">
        {ir.nodes.map((node) => (
          <Block key={node.id} node={node} />
        ))}
      </div>
    </div>
  )
}
