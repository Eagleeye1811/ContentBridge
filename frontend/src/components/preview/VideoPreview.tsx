import type { ContentIR } from '@/types/api'

/** Mirrors the backend estimate (2.5 words per second, 1.5 s floor). */
function spokenSeconds(text: string | null | undefined): number {
  const words = (text ?? '').split(/\s+/).filter(Boolean).length
  return words ? Math.max(1.5, words / 2.5) : 0
}

function clock(seconds: number): string {
  const s = Math.round(seconds)
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

/** The video as a storyboard: each scene with its time, voice-over and visuals. */
export default function VideoPreview({ ir, screen }: { ir: ContentIR; screen?: string }) {
  const scenes = ir.nodes.filter((n) => n.kind === 'scene')
  const intro = ir.nodes.find((n) => n.kind === 'paragraph')
  const vertical = screen === 'vertical'
  let start = 0
  const timed = scenes.map((s) => {
    const from = start
    start += spokenSeconds(s.text) + 0.5
    return { scene: s, from, to: from + spokenSeconds(s.text) }
  })

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      <div className="rounded-xl border border-ink-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold tracking-tight">{ir.title}</h1>
        {intro?.text && <p className="mt-2 text-[15px] leading-relaxed text-ink-600">{intro.text}</p>}
        <p className="mt-3 text-sm text-ink-400">
          {scenes.length} scenes · about {clock(start)} · {vertical ? 'Vertical 9:16' : 'Wide 16:9'}
        </p>
      </div>

      {timed.map(({ scene, from, to }, i) => (
        <div
          key={scene.id}
          className="grid gap-4 rounded-xl border border-ink-200 bg-white p-4 shadow-sm sm:grid-cols-[11rem_minmax(0,1fr)]"
        >
          {/* A frame sketch: what the viewer sees */}
          <div
            className={`relative flex items-center justify-center overflow-hidden rounded-lg bg-ink-900 p-3 text-center ${
              vertical ? 'mx-auto aspect-[9/16] w-28' : 'aspect-video w-full'
            }`}
          >
            <span className="absolute left-2 top-1.5 text-[10px] font-semibold text-ink-400">
              {i + 1}
            </span>
            <div className="space-y-1">
              {(scene.items ?? []).map((overlay, j) => (
                <p key={j} className="text-xs font-semibold leading-tight text-white">
                  {overlay}
                </p>
              ))}
            </div>
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="font-semibold">{scene.title}</p>
              <span className="font-mono text-xs text-ink-400">
                {clock(from)} – {clock(to)}
              </span>
            </div>
            {scene.text && (
              <p className="mt-2 text-[15px] leading-relaxed">
                <span className="mr-1.5 text-xs font-semibold uppercase tracking-wide text-ink-400">
                  Voice-over
                </span>
                {scene.text}
              </p>
            )}
            {scene.notes && (
              <p className="mt-2 text-sm text-ink-600">
                <span className="mr-1.5 text-xs font-semibold uppercase tracking-wide text-ink-400">
                  Visuals
                </span>
                {scene.notes}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
