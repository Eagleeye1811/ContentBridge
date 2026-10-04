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
    accent: 'bg-blue-800 text-blue-800',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  midnight_dark: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-500 text-sky-500',
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
    accent: 'bg-indigo-700 text-indigo-700',
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
    accent: 'bg-teal-700 text-teal-700',
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
    accent: 'bg-blue-800 text-blue-800',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  corporate_blue_grey: {
    bg: 'bg-white',
    text: 'text-slate-900',
    subtext: 'text-slate-600',
    accent: 'bg-blue-800 text-blue-800',
    cardBg: 'bg-slate-50',
    border: 'border-slate-200',
  },
  dark_charcoal_blue: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-500 text-sky-500',
    cardBg: 'bg-slate-900',
    border: 'border-slate-800',
  },
  dark_executive: {
    bg: 'bg-slate-950',
    text: 'text-slate-100',
    subtext: 'text-slate-400',
    accent: 'bg-sky-500 text-sky-500',
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
        className={`relative ${onSelectSlide ? 'cursor-pointer group' : ''}`}
      >
        <SlideFrame number={1} total={total} theme={activeTheme}>
          <TitleSlideContent title={ir.title} theme={activeTheme} />
        </SlideFrame>
        {onSelectSlide && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/0 opacity-0 group-hover:bg-slate-900/5 group-hover:opacity-100 backdrop-blur-[1px] transition-all duration-300">
             <button className="bg-brand-600 text-white px-6 py-2.5 rounded-full text-sm font-bold shadow-xl shadow-brand-500/30 flex items-center gap-2 transform translate-y-4 group-hover:translate-y-0 transition-transform">
               Edit Slide
             </button>
          </div>
        )}
      </div>

      {/* Slide Deck */}
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
            <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/0 opacity-0 group-hover:bg-slate-900/5 group-hover:opacity-100 backdrop-blur-[1px] transition-all duration-300">
               <button className="bg-brand-600 text-white px-6 py-2.5 rounded-full text-sm font-bold shadow-xl shadow-brand-500/30 flex items-center gap-2 transform translate-y-4 group-hover:translate-y-0 transition-transform">
                 Edit Slide
               </button>
            </div>
          )}

          {node.notes && (
            <p className="mt-2 px-1 text-xs leading-relaxed text-ink-600 relative z-10">
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
      className={`relative aspect-video w-full overflow-hidden border ${theme.border} ${theme.bg} ${theme.text} shadow-sm transition-all`}
    >
      {/* Ambient background accents */}
      <div className={`absolute -top-[30%] -right-[10%] w-[60%] h-[70%] rounded-full opacity-[0.03] blur-3xl pointer-events-none ${theme.accent.split(' ')[0]}`} />
      <div className={`absolute -bottom-[20%] -left-[10%] w-[40%] h-[50%] rounded-full opacity-[0.02] blur-3xl pointer-events-none ${theme.accent.split(' ')[0]}`} />
      
      <div className="relative z-10 w-full h-full">
        {children}
      </div>
      <div className={`absolute bottom-[4%] right-[4%] text-[10px] font-medium tracking-wider z-20 ${theme.subtext}`}>
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
  theme: (typeof THEME_STYLES)['navy_white']
}) {
  return (
    <div className="flex h-full flex-col justify-center px-[10%]">
      <h1 className="text-[clamp(1.8rem,4vw,3.2rem)] font-extrabold leading-[1.15] tracking-tight text-slate-900 pb-5">
        {title}
      </h1>
      <div className={`h-[4px] w-[100px] ${theme.accent.split(' ')[0]}`} />
      <p className={`mt-6 text-[clamp(0.85rem,1.5vw,1.1rem)] font-medium tracking-widest uppercase ${theme.subtext}`}>
        Executive Presentation
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
  let layout = (node.layout || 'standard_bullet').toLowerCase()
  const titleStr = (node.title || '').toLowerCase()
  if (titleStr.includes('roadmap') || titleStr.includes('timeline')) {
    layout = 'process'
  }
  if (titleStr.includes('metric') || titleStr.includes('takeaway')) {
    layout = 'metrics'
  }
  const items = (node.items || []).filter((i) => i.trim().length > 0)
  const bgAccent = theme.accent.split(' ')[0]
  const textAccent = theme.accent.split(' ')[1]

  // 1. SECTION DIVIDER
  if (layout === 'section_divider') {
    return (
      <div className={`flex h-full flex-col justify-center px-[12%] ${bgAccent}`}>
        <h2 className="text-[clamp(1.6rem,4vw,2.8rem)] font-bold text-white leading-tight">
          {node.title || node.text}
        </h2>
        <div className="mt-6 h-[2px] w-[15%] bg-white/40" />
      </div>
    )
  }

  // 2. TWO-COLUMN LAYOUT
  if (layout === 'two_column' && items.length > 1) {
    const mid = Math.ceil(items.length / 2)
    const left = items.slice(0, mid)
    const right = items.slice(mid)
    return (
      <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
        <HeaderBar title={node.title || 'Analysis'} theme={theme} />
        <div className="mt-10 flex-1 grid grid-cols-2 gap-16 relative">
          {/* Subtle vertical divider */}
          <div className={`absolute top-0 bottom-10 left-1/2 w-[1px] -translate-x-1/2 ${theme.border} opacity-50`} />
          <ul className="space-y-6">
            {left.map((item, i) => (
              <li key={i} className="flex gap-4 items-start">
                <span className={`mt-2 h-2 w-2 rounded-sm shrink-0 ${bgAccent}`} />
                <span className="text-[clamp(0.8rem,1.4vw,1rem)] leading-relaxed text-slate-700 font-medium tracking-tight">
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <ul className="space-y-6">
            {right.map((item, i) => (
              <li key={i} className="flex gap-4 items-start">
                <span className={`mt-2 h-2 w-2 rounded-sm shrink-0 ${bgAccent}`} />
                <span className="text-[clamp(0.8rem,1.4vw,1rem)] leading-relaxed text-slate-700 font-medium tracking-tight">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    )
  }

  // 3. PROCESS DIAGRAM / TIMELINE LAYOUT
  if ((layout === 'process' || layout === 'timeline') && items.length > 0) {
    const mainItems = items.slice(0, 4)
    const extraItems = items.slice(4)

    return (
      <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
        <HeaderBar title={node.title || 'Roadmap & Process'} theme={theme} />
        
        <div className="mt-4 flex-1 flex flex-col justify-start">
          <div className="relative flex justify-between w-full mt-2">
            {/* Horizontal Line connecting items perfectly centered to the dots */}
            <div className={`absolute top-3 left-0 w-[95%] h-[2px] ${bgAccent} opacity-20 z-0`} />
            
            {mainItems.map((item, idx) => {
              const parts = item.split(/[:\-]/, 2)
              const title = parts.length > 1 && parts[0].length < 40 ? parts[0].trim() : `Phase 0${idx + 1}`
              const desc = parts.length > 1 && parts[0].length < 40 ? item.slice(parts[0].length + 1).trim() : item

              const widthClass = mainItems.length === 1 ? 'w-[80%]' :
                                 mainItems.length === 2 ? 'w-[45%]' :
                                 mainItems.length === 3 ? 'w-[30%]' : 'w-[22%]'

              return (
                <div key={idx} className={`relative z-10 flex flex-col ${widthClass}`}>
                  {/* Clean connected dots */}
                  <div className={`h-6 w-6 rounded-full border-[4px] ${theme.bg} ${bgAccent} shadow-sm z-10`} />
                  <div className="mt-5 border-t-2 border-slate-900 w-8 mb-3" />
                  <h3 className={`font-bold text-[clamp(0.75rem,1.2vw,0.9rem)] text-slate-900 uppercase tracking-widest leading-tight`}>
                    {title}
                  </h3>
                  <p className={`mt-3 text-[clamp(0.7rem,1.1vw,0.85rem)] leading-relaxed text-slate-600 font-medium`}>
                    {desc}
                  </p>
                </div>
              )
            })}
          </div>

          {extraItems.length > 0 && (
            <div className={`mt-12 pt-6 border-t ${theme.border}`}>
              <h4 className={`text-[clamp(0.65rem,1vw,0.75rem)] font-bold uppercase tracking-widest mb-4 ${textAccent}`}>
                Additional Context
              </h4>
              <div className="grid grid-cols-2 gap-x-12 gap-y-3">
                {extraItems.map((item, idx) => (
                  <div key={idx} className="flex gap-3 items-start text-[clamp(0.7rem,1.1vw,0.85rem)] text-slate-600 font-medium">
                    <span className={`${textAccent} font-bold`}>•</span>
                    <span className="leading-relaxed">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  // 4. KEY METRICS / FINANCIAL BREAKDOWN
  if ((layout === 'metrics' || layout === 'key_takeaways') && items.length > 0) {
    const mainItems = items.slice(0, 4)
    const extraItems = items.slice(4)

    const parsedItems = mainItems.map(item => {
      let fig = "";
      let desc = item;
      if (item.includes(":") && item.split(":")[0].length < 25) {
        const parts = item.split(":");
        fig = parts[0].trim();
        desc = parts.slice(1).join(":").trim();
      } else if (item.includes(" - ") && item.split(" - ")[0].length < 25) {
        const parts = item.split(" - ");
        fig = parts[0].trim();
        desc = parts.slice(1).join(" - ").trim();
      } else {
        const match = item.match(/(?:^|\s)([$€£₹]\s*[\d.,]+|[\d.,]+\s*(?:Cr|M|K|B|%|crore|million|billion))(?:\s|$|[,.])/i);
        if (match) {
          fig = match[1].trim();
          desc = item.replace(match[1], "").replace(/\s+/g, " ").replace(/^[,.\s]+|[,.\s]+$/g, "").trim();
          if (desc) desc = desc.charAt(0).toUpperCase() + desc.slice(1);
        }
      }
      return { fig, desc }
    })

    const withFig = parsedItems.filter(i => i.fig)
    const withoutFig = parsedItems.filter(i => !i.fig)

    // INTELLIGENT SPLIT LAYOUT (User requested)
    if (withFig.length > 0 && withoutFig.length > 0 && mainItems.length === 3) {
      return (
        <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
          <HeaderBar title={node.title || 'Key Financials & Metrics'} theme={theme} />
          <div className="mt-6 flex-1 grid grid-cols-2 gap-16 relative">
            {/* Thin vertical line divider */}
            <div className={`absolute top-0 bottom-10 left-1/2 w-[1px] -translate-x-1/2 ${theme.border} opacity-50`} />
            
            {/* Left Side: Figures */}
            <div className="flex flex-col gap-4 justify-start mt-0">
               {withFig.map((item, idx) => (
                  <div key={idx} className="flex flex-col pr-8">
                     <span className={`text-[clamp(1.8rem,3.8vw,3rem)] font-light ${textAccent} tracking-tighter leading-none mb-1`}>{item.fig}</span>
                     <div className={`h-[2px] w-8 ${bgAccent} mb-2`} />
                     <span className={`text-[clamp(0.75rem,1.1vw,0.85rem)] leading-relaxed text-slate-700 font-medium`}>{item.desc}</span>
                  </div>
               ))}
            </div>

            {/* Right Side: Text only */}
            <div className="flex flex-col gap-4 justify-start pl-8 mt-0 h-full">
               {withoutFig.map((item, idx) => (
                  <div key={idx} className="flex flex-col justify-start">
                     <span className={`text-[clamp(0.85rem,1.3vw,1rem)] font-bold ${textAccent} opacity-80 mb-2`}>Key Requirement</span>
                     <span className={`text-[clamp(0.8rem,1.2vw,0.9rem)] leading-relaxed text-slate-700 font-medium`}>{item.desc}</span>
                  </div>
               ))}
            </div>
          </div>
        </div>
      )
    }

    // STANDARD GRID LAYOUT
    return (
      <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
        <HeaderBar title={node.title || 'Key Financials & Metrics'} theme={theme} />
        <div className="mt-10 flex-1 flex flex-col justify-start">
          <div className={`grid gap-x-6 gap-y-8 ${
            mainItems.length === 1 ? 'grid-cols-1' :
            mainItems.length === 2 ? 'grid-cols-2' :
            mainItems.length === 3 ? 'grid-cols-3' :
            'grid-cols-2 sm:grid-cols-4'
          }`}>
            {parsedItems.map((item, idx) => (
              <div key={idx} className={`relative flex flex-col h-full rounded-xl bg-slate-50 border ${theme.border} p-5 shadow-sm`}>
                <div className={`absolute top-4 right-4 text-[0.75rem] font-bold tracking-widest ${theme.subtext} opacity-50`}>
                  {String(idx + 1).padStart(2, '0')}
                </div>
                {item.fig && (
                  <span className={`mt-2 text-[clamp(1.6rem,3vw,2.4rem)] font-light ${textAccent} tracking-tight leading-none mb-3`}>
                    {item.fig}
                  </span>
                )}
                <div className={`h-[2px] w-8 ${bgAccent} mb-4 ${!item.fig ? 'mt-2' : ''}`} />
                <span className={`text-[clamp(0.8rem,1.3vw,0.95rem)] leading-relaxed text-slate-700 font-medium`}>
                  {item.desc}
                </span>
              </div>
            ))}
          </div>
          
          {extraItems.length > 0 && (
             <div className={`mt-auto text-[clamp(0.75rem,1.2vw,0.85rem)] text-slate-500 border-l-4 ${theme.border} pl-5 max-w-4xl py-1 font-medium`}>
               {extraItems.join(' ')}
             </div>
          )}
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
      <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
        <HeaderBar title={node.title || 'Data Overview'} theme={theme} />
        <div className="mt-8 flex-1 overflow-hidden">
          <table className="w-full text-left text-[clamp(0.75rem,1.2vw,0.9rem)] border-collapse">
            <thead>
              <tr className={`border-b-2 border-slate-900`}>
                {(rows[0] || []).map((h, i) => (
                  <th key={i} className={`px-3 py-4 font-bold uppercase tracking-widest text-[0.65rem] text-slate-500`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(1, 7).map((r, ri) => (
                <tr key={ri} className={`border-b ${theme.border} transition-colors hover:bg-slate-50`}>
                  {r.map((c, ci) => (
                    <td key={ci} className={`px-3 py-4 leading-relaxed ${ci === 0 ? 'font-bold text-slate-900' : 'text-slate-600 font-medium'}`}>
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
    <div className="flex h-full flex-col px-[8%] pt-[7%] pb-[7%]">
      <HeaderBar title={node.title || 'Overview'} theme={theme} />
      <div className="mt-10 flex-1">
        <ul className="space-y-6">
          {items.map((item, i) => (
            <li key={i} className="flex gap-5 items-start">
              <span className={`mt-2.5 h-2 w-2 rounded-sm shrink-0 ${bgAccent}`} />
              <span className="text-[clamp(0.9rem,1.5vw,1.1rem)] leading-relaxed text-slate-700 font-medium tracking-tight">{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function HeaderBar({ title, theme }: { title: string; theme: any }) {
  return (
    <div className="relative mb-2">
      <h2 className="text-[clamp(1.5rem,3vw,2.2rem)] font-extrabold text-slate-900 tracking-tight pb-4">{title}</h2>
      <div className={`h-[4px] w-[60px] ${theme.accent.split(' ')[0]}`} />
    </div>
  )
}
