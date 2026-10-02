import type { ContentIR, IRNode } from '@/types/api'

export interface DeckPreviewProps {
  ir: ContentIR
  theme?: string
  selectedIndex?: number
  onSelectSlide?: (index: number) => void
}

const THEME_STYLES: Record<
  string,
  { bg: string; text: string; subtext: string; accent: string; cardBg: string; border: string }
> = {
  corporate_blue: {
    bg: 'bg-white',
    text: 'text-slate-900',
    subtext: 'text-slate-600',
    accent: 'bg-blue-700 text-blue-700',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  midnight_dark: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-400 text-sky-400',
    cardBg: 'bg-slate-900',
    border: 'border-slate-800',
  },
  minimal_monochrome: {
    bg: 'bg-white',
    text: 'text-zinc-900',
    subtext: 'text-zinc-500',
    accent: 'bg-zinc-800 text-zinc-800',
    cardBg: 'bg-zinc-100',
    border: 'border-zinc-200',
  },
  modern_gradient: {
    bg: 'bg-slate-50',
    text: 'text-indigo-950',
    subtext: 'text-indigo-600',
    accent: 'bg-indigo-600 text-indigo-600',
    cardBg: 'bg-indigo-50/70',
    border: 'border-indigo-200',
  },
  academic_research: {
    bg: 'bg-stone-50',
    text: 'text-stone-900',
    subtext: 'text-stone-600',
    accent: 'bg-amber-900 text-amber-900',
    cardBg: 'bg-stone-100',
    border: 'border-stone-300',
  },
  data_analytics: {
    bg: 'bg-white',
    text: 'text-slate-900',
    subtext: 'text-slate-600',
    accent: 'bg-teal-600 text-teal-600',
    cardBg: 'bg-teal-50/60',
    border: 'border-teal-200',
  },
  warm_editorial: {
    bg: 'bg-amber-50/40',
    text: 'text-stone-900',
    subtext: 'text-amber-800',
    accent: 'bg-orange-700 text-orange-700',
    cardBg: 'bg-orange-50/60',
    border: 'border-orange-200',
  },
  high_contrast: {
    bg: 'bg-black',
    text: 'text-white',
    subtext: 'text-yellow-300',
    accent: 'bg-yellow-400 text-yellow-400',
    cardBg: 'bg-zinc-900',
    border: 'border-white',
  },
  navy_white: {
    bg: 'bg-white',
    text: 'text-slate-900',
    subtext: 'text-slate-600',
    accent: 'bg-blue-700 text-blue-700',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  corporate_blue_grey: {
    bg: 'bg-white',
    text: 'text-slate-900',
    subtext: 'text-slate-600',
    accent: 'bg-blue-700 text-blue-700',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  dark_charcoal_blue: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-400 text-sky-400',
    cardBg: 'bg-slate-900',
    border: 'border-slate-800',
  },
  dark_executive: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-400 text-sky-400',
    cardBg: 'bg-slate-900',
    border: 'border-slate-800',
  },
}

/** Rich Presentation Deck Preview rendering themes & responsive visual slide layouts. */
export default function DeckPreview({
  ir,
  theme = 'corporate_blue',
  selectedIndex,
  onSelectSlide,
}: DeckPreviewProps) {
  const slides = ir.nodes.filter((n) => n.kind === 'slide')
  const total = slides.length + 1
  const activeTheme = THEME_STYLES[theme] || THEME_STYLES.navy_white

  // If a specific slide is selected, view that single slide canvas
  if (selectedIndex !== undefined && selectedIndex >= 0) {
    if (selectedIndex === 0) {
      return (
        <SlideFrame number={1} total={total} theme={activeTheme}>
          <TitleSlideContent title={ir.title} theme={activeTheme} />
        </SlideFrame>
      )
    }

    const slideNode = slides[selectedIndex - 1]
    if (!slideNode) return null
    return (
      <SlideFrame number={selectedIndex + 1} total={total} theme={activeTheme}>
        <SlideNodeContent node={slideNode} theme={activeTheme} />
      </SlideFrame>
    )
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-8">
      {/* Title Slide */}
      <div
        onClick={() => onSelectSlide?.(0)}
        className={onSelectSlide ? 'cursor-pointer transition hover:opacity-95' : ''}
      >
        <SlideFrame number={1} total={total} theme={activeTheme}>
          <TitleSlideContent title={ir.title} theme={activeTheme} />
        </SlideFrame>
      </div>

      {/* Slide Deck */}
      {slides.map((node, index) => (
        <div
          key={node.id}
          onClick={() => onSelectSlide?.(index + 1)}
          className={onSelectSlide ? 'cursor-pointer transition hover:opacity-95' : ''}
        >
          <SlideFrame number={index + 2} total={total} theme={activeTheme}>
            <SlideNodeContent node={node} theme={activeTheme} />
          </SlideFrame>
          {node.notes && (
            <p className="mt-2 px-1 text-xs leading-relaxed text-ink-600">
              <span className="font-semibold text-ink-500">Speaker notes: </span>
              {node.notes}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

function SlideFrame({
  number,
  total,
  theme,
  children,
}: {
  number: number
  total: number
  theme: (typeof THEME_STYLES)['navy_white']
  children: React.ReactNode
}) {
  return (
    <div
      className={`relative aspect-video w-full overflow-hidden rounded-2xl border ${theme.border} ${theme.bg} ${theme.text} shadow-sm transition-all`}
    >
      {children}
      <span className={`absolute bottom-[4%] right-[4%] text-[11px] ${theme.subtext}`}>
        {number} / {total}
      </span>
    </div>
  )
}

function TitleSlideContent({
  title,
  theme,
}: {
  title: string
  theme: (typeof THEME_STYLES)['navy_white']
}) {
  return (
    <div className="flex h-full flex-col justify-center px-[8%]">
      <div className={`mb-[4%] h-1.5 w-[16%] rounded-full ${theme.accent.split(' ')[0]}`} />
      <h1 className="text-[clamp(1.2rem,3.4vw,2.2rem)] font-bold leading-tight tracking-tight">
        {title}
      </h1>
      <p className={`mt-3 text-[clamp(0.75rem,1.5vw,1rem)] ${theme.subtext}`}>
        AI Presentation Studio
      </p>
    </div>
  )
}

function SlideNodeContent({
  node,
  theme,
}: {
  node: IRNode
  theme: (typeof THEME_STYLES)['navy_white']
}) {
  const layout = (node.layout || 'standard_bullet').toLowerCase()
  const items = (node.items || []).filter((i) => i.trim().length > 0)

  // 1. Section Divider Layout
  if (layout === 'section_divider') {
    return (
      <div className="flex h-full flex-col items-center justify-center p-[8%] text-center">
        <div className={`rounded-2xl border ${theme.border} ${theme.cardBg} p-8 shadow-inner`}>
          <h2 className="text-[clamp(1.1rem,2.8vw,2rem)] font-bold">{node.title || node.text}</h2>
        </div>
      </div>
    )
  }

  // 2. Two-Column Layout
  if (layout === 'two_column' && items.length > 1) {
    const mid = Math.ceil(items.length / 2)
    const left = items.slice(0, mid)
    const right = items.slice(mid)
    return (
      <div className="flex h-full flex-col px-[6%] pt-[5%] pb-[8%]">
        <HeaderBar title={node.title || 'Analysis'} theme={theme} />
        <div className="mt-4 grid flex-1 grid-cols-2 gap-4">
          <div className={`rounded-xl border ${theme.border} ${theme.cardBg} p-4 text-xs sm:text-sm`}>
            <ul className="space-y-2">
              {left.map((item, i) => (
                <li key={i} className="flex gap-2">
                  <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${theme.accent.split(' ')[0]}`} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className={`rounded-xl border ${theme.border} ${theme.cardBg} p-4 text-xs sm:text-sm`}>
            <ul className="space-y-2">
              {right.map((item, i) => (
                <li key={i} className="flex gap-2">
                  <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${theme.accent.split(' ')[0]}`} />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    )
  }

  // 3. Process Diagram / Timeline Layout
  if ((layout === 'process' || layout === 'timeline') && items.length > 0) {
    return (
      <div className="flex h-full flex-col px-[6%] pt-[5%] pb-[8%]">
        <HeaderBar title={node.title || 'Process Flow'} theme={theme} />
        <div className="mt-6 grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
          {items.slice(0, 4).map((item, idx) => (
            <div
              key={idx}
              className={`flex flex-col rounded-xl border ${theme.border} ${theme.cardBg} p-3 text-xs shadow-xs`}
            >
              <div
                className={`mb-2 flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-bold text-white ${theme.accent.split(' ')[0]}`}
              >
                {idx + 1}
              </div>
              <p className="line-clamp-4 leading-snug">{item}</p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // 4. Key Metrics Cards Layout
  if ((layout === 'metrics' || layout === 'key_takeaways') && items.length > 0) {
    return (
      <div className="flex h-full flex-col px-[6%] pt-[5%] pb-[8%]">
        <HeaderBar title={node.title || 'Key Metrics'} theme={theme} />
        <div className="mt-6 grid flex-1 grid-cols-2 gap-4 sm:grid-cols-3">
          {items.slice(0, 3).map((item, idx) => {
            const parts = item.includes(':') ? item.split(':') : item.split(' - ')
            const fig = parts.length > 1 ? parts[0] : `#${idx + 1}`
            const desc = parts.length > 1 ? parts[1] : item
            return (
              <div
                key={idx}
                className={`flex flex-col items-center justify-center rounded-xl border ${theme.border} ${theme.cardBg} p-4 text-center`}
              >
                <span className={`text-[clamp(1.1rem,2.2vw,1.8rem)] font-extrabold ${theme.accent.split(' ')[1]}`}>
                  {fig}
                </span>
                <span className="mt-1 line-clamp-3 text-xs leading-tight">{desc}</span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // 5. Table Layout
  if ((layout === 'table' || node.rows) && (node.rows?.length || items.length)) {
    const rows = node.rows || [
      ['Metric', 'Value'],
      ...items.map((it, idx) => [`Item ${idx + 1}`, it]),
    ]
    return (
      <div className="flex h-full flex-col px-[6%] pt-[5%] pb-[8%]">
        <HeaderBar title={node.title || 'Data Table'} theme={theme} />
        <div className="mt-4 flex-1 overflow-hidden rounded-xl border border-ink-200">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className={`border-b ${theme.border} ${theme.cardBg} font-semibold`}>
                {(rows[0] || []).map((h, i) => (
                  <th key={i} className="px-3 py-2">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(1, 5).map((r, ri) => (
                <tr key={ri} className={`border-b ${theme.border}`}>
                  {r.map((c, ci) => (
                    <td key={ci} className="px-3 py-1.5">
                      {c}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // 6. Standard Bullet Layout (Default)
  return (
    <div className="flex h-full flex-col px-[7%] pt-[6%]">
      <HeaderBar title={node.title || 'Slide'} theme={theme} />
      <ul className="mt-[3%] space-y-[2%] text-[clamp(0.75rem,1.6vw,1.05rem)] leading-snug">
        {items.map((item, i) => (
          <li key={i} className="flex gap-3">
            <span className={`mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full ${theme.accent.split(' ')[0]}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function HeaderBar({
  title,
  theme,
}: {
  title: string
  theme: (typeof THEME_STYLES)['navy_white']
}) {
  return (
    <div>
      <div className={`mb-2 h-1 w-[12%] rounded-full ${theme.accent.split(' ')[0]}`} />
      <h2 className="text-[clamp(0.95rem,2.2vw,1.5rem)] font-bold leading-snug">{title}</h2>
    </div>
  )
}
