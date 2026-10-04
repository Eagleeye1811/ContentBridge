import type { ContentIR, IRNode } from '@/types/api'

export interface DeckPreviewProps {
  ir: ContentIR
  theme?: string
  selectedIndex?: number
  onSelectSlide?: (index: number) => void
}

export interface ThemeStyle {
  name: string
  bg: string
  text: string
  body: string
  subtext: string
  accentBg: string
  accentText: string
  cardBg: string
  cardText: string
  cardSubtext: string
  border: string
  tableHeaderBg: string
  tableHeaderText: string
  tableRowAlt: string
  isDark: boolean
}

const THEME_STYLES: Record<string, ThemeStyle> = {
  corporate_blue: {
    name: 'Corporate Blue',
    bg: 'bg-white',
    text: 'text-slate-900',
    body: 'text-slate-700',
    subtext: 'text-slate-500',
    accentBg: 'bg-blue-700',
    accentText: 'text-blue-700',
    cardBg: 'bg-blue-50/70',
    cardText: 'text-slate-900',
    cardSubtext: 'text-slate-600',
    border: 'border-blue-200/80',
    tableHeaderBg: 'bg-blue-800',
    tableHeaderText: 'text-white',
    tableRowAlt: 'bg-blue-50/40',
    isDark: false,
  },
  midnight_dark: {
    name: 'Midnight Dark',
    bg: 'bg-slate-950',
    text: 'text-slate-50',
    body: 'text-slate-200',
    subtext: 'text-slate-400',
    accentBg: 'bg-sky-400',
    accentText: 'text-sky-300',
    cardBg: 'bg-slate-900',
    cardText: 'text-slate-100',
    cardSubtext: 'text-slate-300',
    border: 'border-slate-800',
    tableHeaderBg: 'bg-slate-800',
    tableHeaderText: 'text-sky-300',
    tableRowAlt: 'bg-slate-900/80',
    isDark: true,
  },
  minimal_monochrome: {
    name: 'Minimal Monochrome',
    bg: 'bg-zinc-50',
    text: 'text-zinc-950',
    body: 'text-zinc-800',
    subtext: 'text-zinc-600',
    accentBg: 'bg-zinc-800',
    accentText: 'text-zinc-900',
    cardBg: 'bg-zinc-100',
    cardText: 'text-zinc-900',
    cardSubtext: 'text-zinc-600',
    border: 'border-zinc-300',
    tableHeaderBg: 'bg-zinc-900',
    tableHeaderText: 'text-white',
    tableRowAlt: 'bg-zinc-200/50',
    isDark: false,
  },
  modern_gradient: {
    name: 'Modern Gradient',
    bg: 'bg-indigo-950',
    text: 'text-indigo-50',
    body: 'text-indigo-100',
    subtext: 'text-indigo-300',
    accentBg: 'bg-indigo-500',
    accentText: 'text-indigo-300',
    cardBg: 'bg-indigo-900/80',
    cardText: 'text-indigo-50',
    cardSubtext: 'text-indigo-200',
    border: 'border-indigo-800',
    tableHeaderBg: 'bg-indigo-800',
    tableHeaderText: 'text-white',
    tableRowAlt: 'bg-indigo-900/40',
    isDark: true,
  },
  academic_research: {
    name: 'Academic Research',
    bg: 'bg-stone-50',
    text: 'text-stone-950',
    body: 'text-stone-800',
    subtext: 'text-stone-600',
    accentBg: 'bg-amber-900',
    accentText: 'text-amber-900',
    cardBg: 'bg-amber-50/70',
    cardText: 'text-stone-900',
    cardSubtext: 'text-stone-600',
    border: 'border-stone-300',
    tableHeaderBg: 'bg-amber-950',
    tableHeaderText: 'text-amber-100',
    tableRowAlt: 'bg-stone-100/80',
    isDark: false,
  },
  data_analytics: {
    name: 'Data & Analytics',
    bg: 'bg-slate-900',
    text: 'text-teal-50',
    body: 'text-slate-100',
    subtext: 'text-teal-300',
    accentBg: 'bg-teal-400',
    accentText: 'text-teal-300',
    cardBg: 'bg-slate-800/90',
    cardText: 'text-teal-50',
    cardSubtext: 'text-slate-300',
    border: 'border-teal-800/80',
    tableHeaderBg: 'bg-teal-900',
    tableHeaderText: 'text-teal-100',
    tableRowAlt: 'bg-slate-800/50',
    isDark: true,
  },
  warm_editorial: {
    name: 'Warm Editorial',
    bg: 'bg-amber-50/30',
    text: 'text-stone-900',
    body: 'text-stone-800',
    subtext: 'text-orange-900',
    accentBg: 'bg-orange-600',
    accentText: 'text-orange-700',
    cardBg: 'bg-orange-100/50',
    cardText: 'text-stone-900',
    cardSubtext: 'text-orange-900',
    border: 'border-orange-200',
    tableHeaderBg: 'bg-orange-900',
    tableHeaderText: 'text-white',
    tableRowAlt: 'bg-orange-100/30',
    isDark: false,
  },
  high_contrast: {
    name: 'High-Contrast Presentation',
    bg: 'bg-black',
    text: 'text-white',
    body: 'text-zinc-100',
    subtext: 'text-yellow-300',
    accentBg: 'bg-yellow-400',
    accentText: 'text-yellow-300',
    cardBg: 'bg-zinc-900',
    cardText: 'text-white',
    cardSubtext: 'text-zinc-300',
    border: 'border-zinc-700',
    tableHeaderBg: 'bg-yellow-400',
    tableHeaderText: 'text-black',
    tableRowAlt: 'bg-zinc-900/90',
    isDark: true,
  },
}

// Map aliases
THEME_STYLES.navy_white = THEME_STYLES.corporate_blue
THEME_STYLES.corporate_blue_grey = THEME_STYLES.corporate_blue
THEME_STYLES.dark_charcoal_blue = THEME_STYLES.midnight_dark
THEME_STYLES.dark_executive = THEME_STYLES.midnight_dark

/** Rich Presentation Deck Preview with contrast-aware dynamic text-fitting & layout validation. */
export default function DeckPreview({
  ir,
  theme = 'corporate_blue',
  selectedIndex,
  onSelectSlide,
}: DeckPreviewProps) {
  const slides = ir.nodes.filter((n) => n.kind === 'slide')
  const total = slides.length + 1
  const activeTheme = THEME_STYLES[theme] || THEME_STYLES.corporate_blue

  // Single slide canvas view mode
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

  // Full slide deck scroll view
  return (
    <div className="mx-auto w-full max-w-4xl space-y-8">
      {/* Title Cover Slide */}
      <div
        onClick={() => onSelectSlide?.(0)}
        className={`relative ${onSelectSlide ? 'cursor-pointer group' : ''}`}
      >
        <SlideFrame number={1} total={total} theme={activeTheme}>
          <TitleSlideContent title={ir.title} theme={activeTheme} />
        </SlideFrame>
        {onSelectSlide && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/0 opacity-0 group-hover:bg-slate-900/10 group-hover:opacity-100 backdrop-blur-[1px] transition-all duration-200 rounded-lg">
            <button className="bg-brand-600 text-white px-5 py-2 rounded-full text-xs font-bold shadow-lg shadow-brand-500/30 flex items-center gap-2 transform translate-y-2 group-hover:translate-y-0 transition-transform">
              Edit Slide 1
            </button>
          </div>
        )}
      </div>

      {/* Content Slide List */}
      {slides.map((node, index) => (
        <div
          key={node.id}
          onClick={() => onSelectSlide?.(index + 1)}
          className={`relative ${onSelectSlide ? 'cursor-pointer group' : ''}`}
        >
          <SlideFrame number={index + 2} total={total} theme={activeTheme}>
            <SlideNodeContent node={node} theme={activeTheme} />
          </SlideFrame>

          {onSelectSlide && (
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-slate-900/0 opacity-0 group-hover:bg-slate-900/10 group-hover:opacity-100 backdrop-blur-[1px] transition-all duration-200 rounded-lg">
              <button className="bg-brand-600 text-white px-5 py-2 rounded-full text-xs font-bold shadow-lg shadow-brand-500/30 flex items-center gap-2 transform translate-y-2 group-hover:translate-y-0 transition-transform">
                Edit Slide {index + 2}
              </button>
            </div>
          )}

          {node.notes && (
            <p className="mt-2 px-1 text-xs leading-relaxed text-ink-600 relative z-10 italic">
              <span className="font-semibold text-ink-700 not-italic">Speaker notes: </span>
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
  theme: ThemeStyle
  children: React.ReactNode
}) {
  return (
    <div
      className={`relative aspect-video w-full overflow-hidden border ${theme.border} ${theme.bg} ${theme.text} shadow-sm transition-colors duration-200 rounded-xl select-none`}
    >
      {/* Background ambient lighting */}
      <div
        className={`absolute -top-[30%] -right-[10%] w-[60%] h-[70%] rounded-full opacity-[0.04] blur-3xl pointer-events-none ${theme.accentBg}`}
      />

      <div className="relative z-10 w-full h-full p-[5%] flex flex-col justify-between overflow-hidden">
        {children}
      </div>

      <div className={`absolute bottom-[3%] right-[4%] text-[10px] font-mono tracking-wider z-20 ${theme.subtext}`}>
        {number} / {total}
      </div>
    </div>
  )
}

function TitleSlideContent({
  title,
  theme,
}: {
  title: string
  theme: ThemeStyle
}) {
  return (
    <div className="flex h-full flex-col justify-center px-[4%] overflow-hidden">
      <h1 className={`text-[clamp(1.4rem,3.2vw,2.6rem)] font-extrabold leading-[1.18] tracking-tight pb-4 break-words ${theme.text}`}>
        {title || 'Presentation Title'}
      </h1>
      <div className={`h-[4px] w-[80px] rounded-full shrink-0 ${theme.accentBg}`} />
      <p className={`mt-5 text-[clamp(0.7rem,1.2vw,0.95rem)] font-semibold tracking-widest uppercase ${theme.subtext}`}>
        Executive Briefing & Synthesis
      </p>
    </div>
  )
}

function HeaderBar({ title, theme }: { title: string; theme: ThemeStyle }) {
  return (
    <div className="relative mb-2 shrink-0">
      <h2 className={`text-[clamp(1.15rem,2.3vw,1.8rem)] font-extrabold tracking-tight pb-2 break-words leading-snug ${theme.text}`}>
        {title}
      </h2>
      <div className={`h-[3px] w-[45px] rounded-full ${theme.accentBg}`} />
    </div>
  )
}

function SlideNodeContent({
  node,
  theme,
}: {
  node: IRNode
  theme: ThemeStyle
}) {
  let layout = (node.layout || 'standard_bullet').toLowerCase()
  const titleStr = (node.title || '').toLowerCase()
  if (titleStr.includes('roadmap') || titleStr.includes('timeline')) {
    layout = 'process'
  }
  if (titleStr.includes('metric') || titleStr.includes('takeaway')) {
    layout = 'metrics'
  }
  const items = (node.items || []).filter((i) => i.trim().length > 0)

  // 1. SECTION DIVIDER
  if (layout === 'section_divider') {
    return (
      <div className={`flex h-full flex-col justify-center px-[8%] rounded-lg ${theme.cardBg} border ${theme.border}`}>
        <h2 className={`text-[clamp(1.4rem,3vw,2.4rem)] font-extrabold leading-tight break-words ${theme.cardText}`}>
          {node.title || node.text || 'Section Briefing'}
        </h2>
        <div className={`mt-4 h-[3px] w-[12%] rounded-full ${theme.accentBg}`} />
      </div>
    )
  }

  // 2. TWO-COLUMN LAYOUT
  if (layout === 'two_column' && items.length > 1) {
    const mid = Math.ceil(items.length / 2)
    const left = items.slice(0, mid)
    const right = items.slice(mid)
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <HeaderBar title={node.title || 'Analysis'} theme={theme} />
        <div className="mt-3 flex-1 grid grid-cols-2 gap-4 min-h-0 overflow-hidden relative">
          <div className={`rounded-xl border ${theme.border} ${theme.cardBg} p-4 flex flex-col justify-start overflow-y-auto`}>
            <ul className="space-y-3">
              {left.map((item, i) => (
                <li key={i} className="flex gap-2.5 items-start text-[clamp(0.72rem,1.15vw,0.88rem)] leading-relaxed">
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${theme.accentBg}`} />
                  <span className={`font-medium break-words ${theme.cardText}`}>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className={`rounded-xl border ${theme.border} ${theme.cardBg} p-4 flex flex-col justify-start overflow-y-auto`}>
            <ul className="space-y-3">
              {right.map((item, i) => (
                <li key={i} className="flex gap-2.5 items-start text-[clamp(0.72rem,1.15vw,0.88rem)] leading-relaxed">
                  <span className={`mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ${theme.accentBg}`} />
                  <span className={`font-medium break-words ${theme.cardText}`}>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    )
  }

  // 3. PROCESS DIAGRAM / TIMELINE LAYOUT
  if ((layout === 'process' || layout === 'timeline') && items.length > 0) {
    const mainItems = items.slice(0, 5)

    return (
      <div className="flex h-full flex-col overflow-hidden">
        <HeaderBar title={node.title || 'Roadmap & Process'} theme={theme} />

        <div className="mt-2 flex-1 flex flex-col justify-center min-h-0">
          <div className="flex gap-3 w-full items-stretch justify-between h-full py-2">
            {mainItems.map((item, idx) => {
              const parts = item.split(/[:\-]/, 2)
              const title = parts.length > 1 && parts[0].length < 30 ? parts[0].trim() : `Phase ${idx + 1}`
              const desc = parts.length > 1 && parts[0].length < 30 ? item.slice(parts[0].length + 1).trim() : item

              return (
                <div
                  key={idx}
                  className={`flex-1 flex flex-col justify-between rounded-xl border ${theme.border} ${theme.cardBg} p-3 min-w-0 shadow-2xs`}
                >
                  <div className="flex items-center justify-between border-b border-black/10 pb-1.5">
                    <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded ${theme.accentBg} text-white`}>
                      0{idx + 1}
                    </span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider truncate max-w-[80%] ${theme.cardSubtext}`}>
                      {title}
                    </span>
                  </div>
                  <p className={`mt-2 text-[clamp(0.68rem,1.05vw,0.82rem)] leading-relaxed font-medium break-words overflow-y-auto ${theme.cardText}`}>
                    {desc}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // 4. KEY METRICS LAYOUT
  if ((layout === 'metrics' || layout === 'key_takeaways') && items.length > 0) {
    const mainItems = items.slice(0, 4)

    const parsedItems = mainItems.map((item) => {
      let fig = ''
      let desc = item
      if (item.includes(':') && item.split(':')[0].length < 25) {
        const parts = item.split(':')
        fig = parts[0].trim()
        desc = parts.slice(1).join(':').trim()
      } else if (item.includes(' - ') && item.split(' - ')[0].length < 25) {
        const parts = item.split(' - ')
        fig = parts[0].trim()
        desc = parts.slice(1).join(' - ').trim()
      } else {
        const match = item.match(
          /(?:^|\s)([$€£₹]\s*[\d.,]+|[\d.,]+\s*(?:Cr|M|K|B|%|crore|million|billion))(?:\s|$|[,.])/i,
        )
        if (match) {
          fig = match[1].trim()
          desc = item
            .replace(match[1], '')
            .replace(/\s+/g, ' ')
            .replace(/^[,.\s]+|[,.\s]+$/g, '')
            .trim()
          if (desc) desc = desc.charAt(0).toUpperCase() + desc.slice(1)
        }
      }
      return { fig, desc }
    })

    return (
      <div className="flex h-full flex-col overflow-hidden">
        <HeaderBar title={node.title || 'Key Financials & Metrics'} theme={theme} />
        <div className="mt-3 flex-1 min-h-0 flex flex-col justify-center">
          <div
            className={`grid gap-3 h-full ${
              mainItems.length === 1
                ? 'grid-cols-1'
                : mainItems.length === 2
                  ? 'grid-cols-2'
                  : mainItems.length === 3
                    ? 'grid-cols-3'
                    : 'grid-cols-2 sm:grid-cols-4'
            }`}
          >
            {parsedItems.map((item, idx) => (
              <div
                key={idx}
                className={`flex flex-col justify-between rounded-xl border ${theme.border} ${theme.cardBg} p-3.5 shadow-2xs overflow-hidden`}
              >
                <div>
                  <div className={`text-[10px] font-bold tracking-wider ${theme.cardSubtext} uppercase mb-1`}>
                    Metric #{idx + 1}
                  </div>
                  {item.fig ? (
                    <span className={`block text-[clamp(1.3rem,2.8vw,2.2rem)] font-extrabold ${theme.accentText} tracking-tight leading-none mb-2 break-words`}>
                      {item.fig}
                    </span>
                  ) : (
                    <div className={`h-[3px] w-6 rounded ${theme.accentBg} mb-2`} />
                  )}
                </div>
                <p className={`text-[clamp(0.7rem,1.1vw,0.85rem)] leading-relaxed font-medium break-words overflow-y-auto ${theme.cardText}`}>
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // 5. DATA TABLE
  if (layout === 'table' || (node.rows && node.rows.length > 0)) {
    const rows = node.rows || [
      ['Category', 'Details'],
      ...items.map((it, idx) => [`Item 0${idx + 1}`, it]),
    ]
    return (
      <div className="flex h-full flex-col overflow-hidden">
        <HeaderBar title={node.title || 'Data Overview'} theme={theme} />
        <div className={`mt-3 flex-1 overflow-auto rounded-xl border ${theme.border} ${theme.cardBg}`}>
          <table className="w-full text-left text-[clamp(0.7rem,1.1vw,0.85rem)] border-collapse">
            <thead>
              <tr className={`${theme.tableHeaderBg} ${theme.tableHeaderText}`}>
                {(rows[0] || []).map((h, i) => (
                  <th key={i} className="px-3 py-2 font-bold uppercase tracking-wider text-[10px]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(1, 8).map((r, ri) => (
                <tr
                  key={ri}
                  className={`border-b ${theme.border} ${ri % 2 === 1 ? theme.tableRowAlt : ''}`}
                >
                  {r.map((c, ci) => (
                    <td
                      key={ci}
                      className={`px-3 py-2 leading-snug break-words ${
                        ci === 0 ? `font-bold ${theme.cardText}` : `${theme.cardSubtext} font-medium`
                      }`}
                    >
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

  // 6. STANDARD BULLET LAYOUT (DEFAULT)
  return (
    <div className="flex h-full flex-col overflow-hidden">
      <HeaderBar title={node.title || 'Overview'} theme={theme} />
      <div className="mt-3 flex-1 overflow-y-auto pr-1">
        <ul className="space-y-3">
          {items.map((item, i) => (
            <li key={i} className="flex gap-3 items-start">
              <span className={`mt-1.5 h-2 w-2 rounded-sm shrink-0 ${theme.accentBg}`} />
              <span className={`text-[clamp(0.82rem,1.3vw,1.02rem)] leading-relaxed font-medium break-words ${theme.body}`}>
                {item}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
