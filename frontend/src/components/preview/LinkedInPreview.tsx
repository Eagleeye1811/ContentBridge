import type { ContentIR } from '@/types/api'

/** A LinkedIn post card: the post's paragraphs, hashtags highlighted. */
export default function LinkedInPreview({ ir }: { ir: ContentIR }) {
  const paragraphs = ir.nodes.flatMap((n) => n.items ?? (n.text ? [n.text] : []))
  const length = paragraphs.join('\n\n').length
  return (
    <div className="mx-auto w-full max-w-xl">
      <div className="rounded-xl border border-ink-200 bg-white shadow-sm">
        <div className="flex items-center gap-3 px-4 pt-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-600 text-lg font-semibold text-white">
            O
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold">Your organisation</p>
            <p className="text-xs text-ink-400">Just now</p>
          </div>
        </div>
        <div className="space-y-3 px-4 py-4 text-[15px] leading-relaxed">
          {paragraphs.map((p, i) => (
            <p key={i}>
              {p.split(/(\s+)/).map((word, j) =>
                word.startsWith('#') ? (
                  <span key={j} className="font-medium text-brand-600">
                    {word}
                  </span>
                ) : (
                  word
                ),
              )}
            </p>
          ))}
        </div>
        <div className="flex gap-6 border-t border-ink-100 px-4 py-2.5 text-sm text-ink-400">
          <span>Like</span>
          <span>Comment</span>
          <span>Repost</span>
          <span>Send</span>
        </div>
      </div>
      <p className="mt-2 text-right text-xs text-ink-400">{length.toLocaleString()} characters</p>
    </div>
  )
}
