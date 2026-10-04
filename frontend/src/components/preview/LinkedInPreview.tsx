import { useState } from 'react'
import type { ContentIR } from '@/types/api'

const LI_BLUE = '#0a66c2'

// ─── SVG Icons ──────────────────────────────────────────────────────────────
function ThumbIcon({ active }: { active?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3m7-9v4a2 2 0 0 1-2 2H9l-2 7h12a2 2 0 0 0 2-2v-5a2 2 0 0 0-2-2h-3"
        stroke={active ? LI_BLUE : '#5f6368'}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CommentIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
        stroke="#5f6368"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function RepostIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"
        stroke="#5f6368"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <line x1="22" y1="2" x2="11" y2="13" stroke="#5f6368" strokeWidth="2" strokeLinecap="round" />
      <polygon
        points="22 2 15 22 11 13 2 9 22 2"
        stroke="#5f6368"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function EllipsisIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
      <circle cx="5" cy="12" r="1.5" />
      <circle cx="12" cy="12" r="1.5" />
      <circle cx="19" cy="12" r="1.5" />
    </svg>
  )
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3 w-3">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
      <path
        d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10A15.3 15.3 0 0 1 12 2z"
        stroke="currentColor"
        strokeWidth="2"
      />
    </svg>
  )
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3 w-3">
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

type PostCategory = 'general' | 'celebrate' | 'hiring' | 'poll' | 'event' | 'document'

type CelebrationType = 'launch' | 'anniversary' | 'position' | 'education' | 'certification'

function detectCategory(text: string): { category: PostCategory; subType?: CelebrationType } {
  const t = text.toLowerCase()
  if (t.includes('hiring') || t.includes('open role') || t.includes('job opening') || t.includes('we are looking')) {
    return { category: 'hiring' }
  }
  if (t.includes('poll') || t.includes('vote') || t.includes('what do you think?')) {
    return { category: 'poll' }
  }
  if (t.includes('event') || t.includes('webinar') || t.includes('conference') || t.includes('summit')) {
    return { category: 'event' }
  }
  if (t.includes('presentation') || t.includes('slides') || t.includes('guide') || t.includes('pdf')) {
    return { category: 'document' }
  }
  if (t.includes('excited to announce') || t.includes('project launch') || t.includes('launching')) {
    return { category: 'celebrate', subType: 'launch' }
  }
  if (t.includes('anniversary') || t.includes('years at')) {
    return { category: 'celebrate', subType: 'anniversary' }
  }
  if (t.includes('promoted') || t.includes('new role') || t.includes('joined')) {
    return { category: 'celebrate', subType: 'position' }
  }
  if (t.includes('certified') || t.includes('certification') || t.includes('passed')) {
    return { category: 'celebrate', subType: 'certification' }
  }
  if (t.includes('graduated') || t.includes('education') || t.includes('degree')) {
    return { category: 'celebrate', subType: 'education' }
  }
  return { category: 'general' }
}

function HighlightedText({ text }: { text: string }) {
  const parts = text.split(/(\s+)/)
  return (
    <>
      {parts.map((word, i) =>
        word.startsWith('#') || word.startsWith('@') ? (
          <span
            key={i}
            style={{ color: LI_BLUE }}
            className="font-medium cursor-pointer hover:underline"
          >
            {word}
          </span>
        ) : (
          word
        ),
      )}
    </>
  )
}

const SEE_MORE_THRESHOLD = 210

export default function LinkedInPreview({ ir }: { ir: ContentIR }) {
  const [expanded, setExpanded] = useState(false)
  const [liked, setLiked] = useState(false)
  const [audience, setAudience] = useState<'Anyone' | 'Connections' | 'Group'>('Anyone')
  const [activeSlide, setActiveSlide] = useState(1)

  const paragraphs = ir.nodes.flatMap((n) =>
    n.kind === 'post' ? (n.items ?? (n.text ? [n.text] : [])) : [],
  )
  const rawParas =
    paragraphs.length > 0
      ? paragraphs
      : ir.nodes.flatMap((n) => n.items ?? (n.text ? [n.text] : []))
  const allParas = rawParas.length > 0 ? rawParas : [ir.title || 'Drafting post...']

  const fullText = allParas.join('\n\n')
  const charCount = fullText.length
  const detected = detectCategory(fullText)

  const [category, setCategory] = useState<PostCategory>(detected.category)
  const [celebrationType, setCelebrationType] = useState<CelebrationType>(
    detected.subType ?? 'launch',
  )
  const [selectedPollOption, setSelectedPollOption] = useState<number | null>(null)

  const needsFold = charCount > SEE_MORE_THRESHOLD && !expanded

  let foldIdx = 0
  let acc = 0
  for (let i = 0; i < allParas.length; i++) {
    acc += allParas[i].length + 2
    if (acc >= SEE_MORE_THRESHOLD) {
      foldIdx = i
      break
    }
    foldIdx = i
  }

  const visibleParas = needsFold ? allParas.slice(0, foldIdx + 1) : allParas
  const hasMediaHint = ir.nodes.some((n) => n.notes && n.notes.length > 0)

  const handleLikeToggle = () => {
    if (liked) {
      setLiked(false)
    } else {
      setLiked(true)
    }
  }

  return (
    <div className="mx-auto w-full max-w-xl text-gray-900" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Top Controls Header Bar */}
      <div className="mb-3 rounded-lg border border-gray-200 bg-white p-3 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 pb-2.5">
          <div className="flex items-center gap-2">
            <div
              className="flex items-center justify-center rounded"
              style={{ background: LI_BLUE, width: 22, height: 22 }}
            >
              <span className="text-[10px] font-extrabold text-white tracking-tighter">in</span>
            </div>
            <span className="text-sm font-bold" style={{ color: LI_BLUE }}>
              LinkedIn Compose & Preview
            </span>
          </div>

          {/* Privacy dropdown selector */}
          <div className="flex items-center gap-1.5 rounded-full border border-gray-300 bg-gray-50 px-2.5 py-1 text-xs font-semibold text-gray-700">
            <GlobeIcon />
            <select
              value={audience}
              onChange={(e) => setAudience(e.target.value as any)}
              className="bg-transparent font-medium text-xs focus:outline-hidden cursor-pointer"
            >
              <option value="Anyone">Anyone (Public)</option>
              <option value="Connections">Connections only</option>
              <option value="Group">Group members</option>
            </select>
            <ChevronDownIcon />
          </div>
        </div>

        {/* Post Type Selector Pills */}
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-gray-400 mr-1">Post Style:</span>
          {(
            [
              { id: 'general', label: '💬 Post' },
              { id: 'celebrate', label: '🎉 Celebrate' },
              { id: 'hiring', label: '💼 Hiring' },
              { id: 'poll', label: '📊 Poll' },
              { id: 'event', label: '📅 Event' },
              { id: 'document', label: '📄 Slide Deck' },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              onClick={() => setCategory(item.id)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-all ${
                category === item.id
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Sub-options for Celebrate */}
        {category === 'celebrate' && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5 pt-2 border-t border-gray-100 text-xs">
            <span className="text-[11px] font-medium text-gray-400">Occasion:</span>
            {(
              [
                { id: 'launch', label: '🚀 Project Launch' },
                { id: 'anniversary', label: '🏆 Work Anniversary' },
                { id: 'position', label: '💼 New Position' },
                { id: 'certification', label: '📜 Certification' },
                { id: 'education', label: '🎓 Education' },
              ] as const
            ).map((sub) => (
              <button
                key={sub.id}
                onClick={() => setCelebrationType(sub.id)}
                className={`rounded-md px-2 py-0.5 text-xs font-medium border ${
                  celebrationType === sub.id
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
                }`}
              >
                {sub.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Main Post Card */}
      <div
        className="overflow-hidden rounded-lg bg-white shadow-sm"
        style={{ border: '1px solid #e0e0e0' }}
      >
        {/* Celebration Special Banner */}
        {category === 'celebrate' && (
          <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 p-4 text-white">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-white/20 p-1.5 text-lg">
                {celebrationType === 'launch' && '🚀'}
                {celebrationType === 'anniversary' && '🏆'}
                {celebrationType === 'position' && '💼'}
                {celebrationType === 'certification' && '📜'}
                {celebrationType === 'education' && '🎓'}
              </span>
              <div>
                <p className="text-xs uppercase font-bold tracking-wider opacity-90">
                  Celebrate an occasion
                </p>
                <p className="text-sm font-semibold">
                  {celebrationType === 'launch' && 'Project Launch Announcement'}
                  {celebrationType === 'anniversary' && 'Celebrating Work Anniversary'}
                  {celebrationType === 'position' && 'New Position / Promotion'}
                  {celebrationType === 'certification' && 'Earned New Certification'}
                  {celebrationType === 'education' && 'Educational Achievement'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Hiring Special Banner */}
        {category === 'hiring' && (
          <div className="bg-emerald-600 p-3.5 text-white flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-700 text-xl font-bold">
                💼
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-emerald-100">
                  WE'RE HIRING
                </p>
                <p className="text-sm font-semibold">Join Our Growing Team!</p>
              </div>
            </div>
            <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-700 shadow-xs">
              Open Role
            </span>
          </div>
        )}

        {/* User Header */}
        <div className="flex items-start justify-between px-4 pt-4 pb-2">
          <div className="flex items-start gap-3">
            <div className="relative">
              <div
                className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-lg font-bold text-white shadow-xs"
                style={{ background: 'linear-gradient(135deg,#0a66c2,#0052a3)' }}
              >
                O
              </div>
              {category === 'hiring' && (
                <div
                  className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-600 border-2 border-white text-[10px] text-white font-bold"
                  title="Hiring Profile Frame"
                >
                  #
                </div>
              )}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <p className="text-sm font-semibold leading-snug hover:underline cursor-pointer" style={{ color: '#000000e0' }}>
                  Your Organisation
                </p>
                <span className="text-xs text-gray-400">· 1st</span>
              </div>
              <p className="text-xs leading-snug" style={{ color: '#5f6368' }}>
                Official Account · 12,400 followers
              </p>
              <div className="mt-0.5 flex items-center gap-1 text-xs" style={{ color: '#5f6368' }}>
                <span>Just now</span>
                <span>·</span>
                <span className="flex items-center gap-0.5">
                  <GlobeIcon />
                  <span className="text-[11px]">{audience}</span>
                </span>
              </div>
            </div>
          </div>
          <button
            className="rounded-full p-1.5 transition-colors hover:bg-gray-100 text-gray-500"
            aria-label="More options"
          >
            <EllipsisIcon />
          </button>
        </div>

        {/* Post Text Body */}
        <div className="px-4 pb-3">
          <div className="space-y-2.5 text-[14.5px] leading-relaxed" style={{ color: '#000000e0' }}>
            {visibleParas.map((p, i) => (
              <p key={i}>
                <HighlightedText text={p} />
              </p>
            ))}
          </div>
          {needsFold && (
            <button
              onClick={() => setExpanded(true)}
              className="mt-1 text-xs font-semibold text-gray-500 transition-colors hover:text-blue-700"
            >
              …see more
            </button>
          )}
        </div>

        {/* Interactive Attachment Views based on Category */}
        {category === 'poll' && (
          <div className="mx-4 mb-3 rounded-lg border border-gray-200 bg-gray-50 p-3.5">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              📊 LinkedIn Poll
            </p>
            <p className="text-sm font-semibold text-gray-900 mb-3">
              What is your primary focus for content strategy this quarter?
            </p>
            <div className="space-y-2">
              {[
                { label: 'Automated Multi-channel Publishing', percent: 62 },
                { label: 'AI Summarization & Compliance', percent: 24 },
                { label: 'Engagement Analytics & Insights', percent: 14 },
              ].map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedPollOption(idx)}
                  className={`w-full rounded-md border p-2.5 text-left text-xs font-medium transition-all ${
                    selectedPollOption === idx
                      ? 'border-blue-600 bg-blue-50 text-blue-800'
                      : 'border-gray-300 bg-white text-gray-800 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>{opt.label}</span>
                    {selectedPollOption !== null && (
                      <span className="font-bold">{opt.percent}%</span>
                    )}
                  </div>
                  {selectedPollOption !== null && (
                    <div className="mt-1.5 h-1.5 w-full rounded-full bg-gray-200 overflow-hidden">
                      <div
                        className="h-full bg-blue-600 rounded-full"
                        style={{ width: `${opt.percent}%` }}
                      />
                    </div>
                  )}
                </button>
              ))}
            </div>
            <p className="mt-2.5 text-[11px] text-gray-400">
              1,420 votes · 6 days left · Select an option to vote
            </p>
          </div>
        )}

        {category === 'event' && (
          <div className="mx-4 mb-3 rounded-lg border border-gray-200 bg-white overflow-hidden shadow-xs">
            <div className="bg-gradient-to-r from-blue-700 to-indigo-800 p-4 text-white flex items-center justify-between">
              <div>
                <span className="rounded bg-blue-500/40 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                  VIRTUAL EVENT
                </span>
                <h4 className="mt-1 text-base font-bold">Content Bridge Live Webinar 2026</h4>
              </div>
              <div className="rounded-lg bg-white p-2 text-center text-gray-900 shadow-xs min-w-[50px]">
                <p className="text-[10px] font-bold text-red-600 uppercase">OCT</p>
                <p className="text-lg font-black leading-none">15</p>
              </div>
            </div>
            <div className="p-3.5 flex items-center justify-between bg-gray-50">
              <div className="text-xs text-gray-600">
                <p className="font-semibold text-gray-800">Thursday, Oct 15 · 4:00 PM - 5:00 PM IST</p>
                <p>Online event · LinkedIn Live</p>
              </div>
              <button className="rounded-full bg-blue-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-blue-700 shadow-xs">
                Attend
              </button>
            </div>
          </div>
        )}

        {category === 'document' && (
          <div className="mx-4 mb-3 rounded-lg border border-gray-200 bg-slate-900 text-white p-4 relative overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-700 pb-2 mb-3">
              <span className="text-xs font-medium text-slate-300">📄 Slide Deck Document</span>
              <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300 font-mono">
                Slide {activeSlide} of 5
              </span>
            </div>
            <div className="py-8 text-center">
              <h4 className="text-lg font-bold text-slate-100">
                {activeSlide === 1 && 'Executive Briefing & Strategy Deck'}
                {activeSlide === 2 && 'Key Objectives & Target Audience'}
                {activeSlide === 3 && 'Multi-Platform Transformation Matrix'}
                {activeSlide === 4 && 'Implementation Roadmap'}
                {activeSlide === 5 && 'Summary & Next Actions'}
              </h4>
              <p className="text-xs text-slate-400 mt-2">
                ContentBridge Enterprise Slide Document
              </p>
            </div>
            <div className="flex items-center justify-between border-t border-slate-700 pt-2.5 text-xs">
              <button
                disabled={activeSlide === 1}
                onClick={() => setActiveSlide((s) => Math.max(1, s - 1))}
                className="disabled:opacity-40 text-blue-400 font-semibold hover:underline"
              >
                ← Previous slide
              </button>
              <button
                disabled={activeSlide === 5}
                onClick={() => setActiveSlide((s) => Math.min(5, s + 1))}
                className="disabled:opacity-40 text-blue-400 font-semibold hover:underline"
              >
                Next slide →
              </button>
            </div>
          </div>
        )}

        {/* Media Placeholder (for general post with media hint or user image) */}
        {category === 'general' && hasMediaHint && (
          <div
            className="mx-4 mb-3 flex h-40 flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed bg-gray-50"
            style={{ borderColor: '#c8cdd5' }}
          >
            <div className="rounded-full bg-gray-200 p-2 text-gray-500">📷</div>
            <p className="text-xs font-semibold text-gray-600">
              Attached Media Preview (1200 × 627 px)
            </p>
            <p className="text-[10px] text-gray-400">Image / Graphic output asset attached</p>
          </div>
        )}

        {/* Reactions Row */}
        <div
          className="flex items-center justify-between border-t px-4 py-2 text-xs text-gray-500"
          style={{ borderColor: '#e0e0e0' }}
        >
          <div className="flex items-center gap-1.5">
            <div className="flex -space-x-1">
              {['👍', '🎉', '💡'].map((emoji, i) => (
                <span
                  key={i}
                  className="flex h-4 w-4 items-center justify-center rounded-full border border-white text-[9px]"
                  style={{ background: '#e8f0fe', zIndex: 3 - i }}
                >
                  {emoji}
                </span>
              ))}
            </div>
            <span>{liked ? 249 : 248}</span>
          </div>
          <div className="flex gap-3">
            <span className="cursor-pointer hover:underline hover:text-blue-600">42 comments</span>
            <span className="cursor-pointer hover:underline hover:text-blue-600">18 reposts</span>
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="flex border-t" style={{ borderColor: '#e0e0e0' }}>
          {[
            {
              icon: <ThumbIcon active={liked} />,
              label: liked ? 'Liked' : 'Like',
              active: liked,
              action: handleLikeToggle,
            },
            { icon: <CommentIcon />, label: 'Comment', active: false, action: undefined },
            { icon: <RepostIcon />, label: 'Repost', active: false, action: undefined },
            { icon: <SendIcon />, label: 'Send', active: false, action: undefined },
          ].map(({ icon, label, active, action }) => (
            <button
              key={label}
              onClick={action}
              className="flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors hover:bg-gray-100"
              style={{ color: active ? LI_BLUE : '#5f6368' }}
            >
              {icon}
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Footer Metrics & Validation */}
      <div className="mt-2 flex items-center justify-between px-1 text-xs">
        <span className="text-gray-500">
          {charCount.toLocaleString()} / 3,000 characters
        </span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
            charCount > 2500
              ? 'bg-amber-100 text-amber-800'
              : 'bg-green-100 text-green-800'
          }`}
        >
          {charCount > 2500 ? '⚠ Long post (Consider folding)' : '✓ Optimal LinkedIn post size'}
        </span>
      </div>
    </div>
  )
}
