import type { ContentIR } from '@/types/api'

const LIMIT = 280

/** X (Twitter) posts as they appear in a feed; a thread is joined by a line. */
export default function TwitterPreview({ ir }: { ir: ContentIR }) {
  const posts = ir.nodes
    .filter((n) => n.kind === 'post')
    .map((n) => (n.items ?? []).filter(Boolean).join('\n'))
  const thread = posts.length > 1

  return (
    <div className="mx-auto w-full max-w-xl rounded-xl border border-ink-200 bg-white shadow-sm">
      {posts.map((text, i) => (
        <div key={i} className="flex gap-3 border-b border-ink-100 px-4 py-4 last:border-0">
          <div className="flex flex-col items-center">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ink-900 text-sm font-semibold text-white">
              O
            </span>
            {thread && i < posts.length - 1 && <span className="mt-1 w-0.5 flex-1 bg-ink-200" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm">
              <span className="font-semibold">Your organisation</span>
              <span className="text-ink-400"> · now</span>
            </p>
            <p className="mt-1 whitespace-pre-line text-[15px] leading-relaxed">
              {text.split(/(\s+)/).map((word, j) =>
                word.startsWith('#') ? (
                  <span key={j} className="text-brand-600">
                    {word}
                  </span>
                ) : (
                  word
                ),
              )}
            </p>
            <p
              className={`mt-2 text-xs ${text.length > LIMIT ? 'font-medium text-red-600' : 'text-ink-400'}`}
            >
              {thread && `${i + 1}/${posts.length} · `}
              {text.length}/{LIMIT} characters
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
