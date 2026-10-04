import { useState } from 'react'
import type { ContentIR } from '@/types/api'

const CHAR_LIMIT = 280

// ── SVG Icons ──────────────────────────────────────────────────────────────
function XLogo() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.259 5.63L18.244 2.25Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z" />
    </svg>
  )
}

function ReplyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function RetweetIcon({ active }: { active?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" style={{ color: active ? '#00ba7c' : 'currentColor' }}>
      <path
        d="M17 1l4 4-4 4M3 11V9a4 4 0 0 1 4-4h14M7 23l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function HeartIcon({ filled }: { filled?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4">
      <path
        d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"
        fill={filled ? '#f91880' : 'none'}
        stroke={filled ? '#f91880' : 'currentColor'}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function BookmarkIcon({ active }: { active?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill={active ? '#1d9bf0' : 'none'} className="h-4 w-4">
      <path
        d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"
        stroke={active ? '#1d9bf0' : 'currentColor'}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function ShareIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <path
        d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function BarChartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4">
      <line x1="18" y1="20" x2="18" y2="10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="12" y1="20" x2="12" y2="4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="6" y1="20" x2="6" y2="14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  )
}

function VerifiedBadge({ type }: { type: 'gold' | 'blue' | 'none' }) {
  if (type === 'none') return null
  const color = type === 'gold' ? '#eac54f' : '#1d9bf0'
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0" style={{ color }}>
      <path
        fill="currentColor"
        d="M22.25 12c0-1.43-.88-2.67-2.19-3.34.46-1.39.2-2.9-.81-3.91-1.01-1-2.52-1.27-3.9-.81C14.66 2.88 13.43 2 12 2s-2.66.88-3.33 2.19c-1.38-.46-2.9-.2-3.91.81-1 1.01-1.26 2.52-.8 3.91C2.87 9.33 2 10.57 2 12s.87 2.67 2.19 3.34c-.46 1.39-.21 2.9.8 3.91 1.01 1 2.53 1.27 3.91.81C9.34 21.12 10.57 22 12 22s2.67-.88 3.34-2.19c1.38.46 2.9.2 3.91-.81.01-.01.98-1.01.81-3.91C21.37 14.67 22.25 13.43 22.25 12zm-6.44-3.96L10.29 14l-2.1-2.1a.75.75 0 1 0-1.06 1.06l2.62 2.63c.29.29.68.44 1.08.44.4 0 .79-.15 1.08-.44l6.08-6.08a.75.75 0 1 0-1.06-1.07l-.38.6z"
      />
    </svg>
  )
}

function XText({ text }: { text: string }) {
  const parts = text.split(/(\s+)/)
  return (
    <>
      {parts.map((word, i) =>
        word.startsWith('#') || word.startsWith('@') ? (
          <span key={i} className="cursor-pointer hover:underline font-normal" style={{ color: '#1d9bf0' }}>
            {word}
          </span>
        ) : (
          word
        ),
      )}
    </>
  )
}

export default function TwitterPreview({ ir }: { ir: ContentIR }) {
  const [likedIdx, setLikedIdx] = useState<Set<number>>(new Set())
  const [retweetedIdx, setRetweetedIdx] = useState<Set<number>>(new Set())
  const [bookmarkedIdx, setBookmarkedIdx] = useState<Set<number>>(new Set())
  const [replySetting, setReplySetting] = useState<'everyone' | 'following' | 'mentioned'>('everyone')
  const [badgeType, setBadgeType] = useState<'gold' | 'blue' | 'none'>('gold')
  const [showPoll, setShowPoll] = useState(false)
  const [pollSelected, setPollSelected] = useState<number | null>(null)

  // Extract posts from IR
  const posts = ir.nodes
    .filter((n) => n.kind === 'post')
    .map((n) => ({
      text: (n.items ?? (n.text ? [n.text] : [])).filter(Boolean).join('\n'),
      hasMedia: Boolean(n.notes && n.notes.length > 0),
    }))

  const tweets =
    posts.length > 0 && posts.some((p) => p.text.trim())
      ? posts
      : [
          {
            text: ir.nodes.flatMap((n) => n.items ?? (n.text ? [n.text] : [])).join('\n') || ir.title || 'Drafting tweet...',
            hasMedia: false,
          },
        ]

  const isThread = tweets.length > 1

  const toggleLike = (i: number) =>
    setLikedIdx((prev) => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })

  const toggleRetweet = (i: number) =>
    setRetweetedIdx((prev) => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })

  const toggleBookmark = (i: number) =>
    setBookmarkedIdx((prev) => {
      const next = new Set(prev)
      next.has(i) ? next.delete(i) : next.add(i)
      return next
    })

  return (
    <div className="mx-auto w-full max-w-xl text-white" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Top Bar with Options */}
      <div className="mb-3 rounded-xl border border-gray-800 bg-gray-950 p-3 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-800 pb-2.5">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-black font-bold">
              <XLogo />
            </div>
            <span className="text-sm font-bold text-white">X / Twitter Compose Preview</span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-400">Badge:</span>
            <select
              value={badgeType}
              onChange={(e) => setBadgeType(e.target.value as any)}
              className="rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs text-white focus:outline-hidden"
            >
              <option value="gold">🥇 Gold (Verified Business)</option>
              <option value="blue">🔹 Blue (Verified User)</option>
              <option value="none">Standard (No Badge)</option>
            </select>
          </div>
        </div>

        {/* Feature Toggles Toolbar */}
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-gray-400">Who can reply:</span>
            <button
              onClick={() =>
                setReplySetting((s) =>
                  s === 'everyone' ? 'following' : s === 'following' ? 'mentioned' : 'everyone',
                )
              }
              className="rounded-full bg-gray-800 px-3 py-1 text-xs font-semibold text-sky-400 hover:bg-gray-700 transition"
            >
              🌐 {replySetting === 'everyone' && 'Everyone'}
              {replySetting === 'following' && 'Accounts you follow'}
              {replySetting === 'mentioned' && 'Only accounts you mention'}
            </button>
          </div>

          <button
            onClick={() => setShowPoll((v) => !v)}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
              showPoll ? 'bg-sky-500 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            📊 {showPoll ? 'Hide Poll' : 'Add Poll Preview'}
          </button>
        </div>
      </div>

      {/* Tweet Container Card */}
      <div
        className="overflow-hidden rounded-2xl shadow-xl"
        style={{ background: '#000000', border: '1px solid #2f3336' }}
      >
        {tweets.map((tweet, i) => {
          const charCount = tweet.text.length
          const overLimit = charCount > CHAR_LIMIT
          const isLiked = likedIdx.has(i)
          const isRetweeted = retweetedIdx.has(i)
          const isBookmarked = bookmarkedIdx.has(i)

          return (
            <div
              key={i}
              className="relative flex gap-3 px-4 pt-4 pb-3"
              style={{
                borderBottom: i < tweets.length - 1 ? '1px solid #2f3336' : 'none',
              }}
            >
              {/* Profile Avatar & Vertical Thread Line */}
              <div className="flex flex-col items-center">
                <div
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white shadow-xs"
                  style={{ background: 'linear-gradient(135deg,#1d9bf0,#0a66c2)' }}
                >
                  O
                </div>
                {isThread && i < tweets.length - 1 && (
                  <div
                    className="mt-1 w-0.5 flex-1"
                    style={{ background: '#333639', minHeight: 28 }}
                  />
                )}
              </div>

              {/* Tweet Content */}
              <div className="min-w-0 flex-1 pb-1">
                {/* Header info */}
                <div className="flex items-center gap-1 text-sm">
                  <span className="font-bold text-white hover:underline cursor-pointer">
                    Your Organisation
                  </span>
                  <VerifiedBadge type={badgeType} />
                  <span className="text-gray-500 text-xs truncate">@org_official</span>
                  <span className="text-gray-500 text-xs">·</span>
                  <span className="text-gray-500 text-xs">now</span>

                  {isThread && (
                    <span className="ml-auto rounded-full bg-gray-900 px-2 py-0.5 text-[11px] font-semibold text-sky-400 border border-gray-800">
                      {i + 1}/{tweets.length}
                    </span>
                  )}
                </div>

                {/* Main Tweet Body */}
                <p className="mt-1.5 whitespace-pre-line text-[15px] leading-[1.5] text-gray-100">
                  <XText text={tweet.text} />
                </p>

                {/* Twitter Poll Preview */}
                {showPoll && i === 0 && (
                  <div className="mt-3 rounded-2xl border border-gray-800 bg-gray-950 p-3">
                    <p className="text-xs font-semibold text-gray-400 mb-2">📊 Quick Poll</p>
                    <div className="space-y-2">
                      {[
                        { label: 'Option A: Real-time API Bridge', percent: 58 },
                        { label: 'Option B: Batch IR Pipeline', percent: 42 },
                      ].map((opt, pIdx) => (
                        <button
                          key={pIdx}
                          onClick={() => setPollSelected(pIdx)}
                          className={`w-full rounded-xl border p-2.5 text-left text-xs font-semibold transition ${
                            pollSelected === pIdx
                              ? 'border-sky-500 bg-sky-950/40 text-sky-400'
                              : 'border-gray-800 bg-gray-900 text-gray-200 hover:border-gray-700'
                          }`}
                        >
                          <div className="flex justify-between items-center">
                            <span>{opt.label}</span>
                            {pollSelected !== null && <span>{opt.percent}%</span>}
                          </div>
                          {pollSelected !== null && (
                            <div className="mt-1.5 h-1.5 w-full rounded-full bg-gray-800 overflow-hidden">
                              <div
                                className="h-full bg-sky-500 rounded-full"
                                style={{ width: `${opt.percent}%` }}
                              />
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                    <p className="mt-2 text-[11px] text-gray-500">842 votes · 23 hours left</p>
                  </div>
                )}

                {/* Media Attachment Grid Placeholder */}
                {tweet.hasMedia && !showPoll && (
                  <div
                    className="mt-3 flex h-44 flex-col items-center justify-center rounded-2xl border border-gray-800 bg-gray-950"
                  >
                    <div className="rounded-full bg-gray-900 p-3 text-sky-400">🖼️</div>
                    <p className="text-xs font-semibold text-gray-300">
                      Media attachment preview (16:9 / 1:1 format)
                    </p>
                    <p className="text-[10px] text-gray-500">Up to 4 images or 1 video</p>
                  </div>
                )}

                {/* Interactive Action Bar */}
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500 max-w-md">
                  {/* Reply */}
                  <button className="flex items-center gap-1.5 transition hover:text-sky-400 group">
                    <div className="rounded-full p-1.5 group-hover:bg-sky-500/10">
                      <ReplyIcon />
                    </div>
                    <span>12</span>
                  </button>

                  {/* Retweet */}
                  <button
                    onClick={() => toggleRetweet(i)}
                    className={`flex items-center gap-1.5 transition group ${
                      isRetweeted ? 'text-emerald-500 font-bold' : 'hover:text-emerald-500'
                    }`}
                  >
                    <div className="rounded-full p-1.5 group-hover:bg-emerald-500/10">
                      <RetweetIcon active={isRetweeted} />
                    </div>
                    <span>{isRetweeted ? 35 : 34}</span>
                  </button>

                  {/* Like */}
                  <button
                    onClick={() => toggleLike(i)}
                    className={`flex items-center gap-1.5 transition group ${
                      isLiked ? 'text-pink-500 font-bold' : 'hover:text-pink-500'
                    }`}
                  >
                    <div className="rounded-full p-1.5 group-hover:bg-pink-500/10">
                      <HeartIcon filled={isLiked} />
                    </div>
                    <span>{isLiked ? 248 : 247}</span>
                  </button>

                  {/* Views */}
                  <button className="flex items-center gap-1.5 transition hover:text-sky-400 group">
                    <div className="rounded-full p-1.5 group-hover:bg-sky-500/10">
                      <BarChartIcon />
                    </div>
                    <span>4.1K</span>
                  </button>

                  {/* Bookmark */}
                  <button
                    onClick={() => toggleBookmark(i)}
                    className={`flex items-center gap-1.5 transition group ${
                      isBookmarked ? 'text-sky-400' : 'hover:text-sky-400'
                    }`}
                  >
                    <div className="rounded-full p-1.5 group-hover:bg-sky-500/10">
                      <BookmarkIcon active={isBookmarked} />
                    </div>
                  </button>

                  {/* Share */}
                  <button className="flex items-center gap-1.5 transition hover:text-sky-400 group">
                    <div className="rounded-full p-1.5 group-hover:bg-sky-500/10">
                      <ShareIcon />
                    </div>
                  </button>
                </div>

                {/* Character gauge / overflow warning */}
                <div className="mt-2.5 flex items-center justify-between border-t border-gray-900 pt-2 text-[11px]">
                  <span className={overLimit ? 'text-red-400 font-bold' : 'text-gray-500'}>
                    {charCount} / {CHAR_LIMIT} characters
                  </span>
                  {overLimit && (
                    <span className="rounded bg-red-950 px-2 py-0.5 text-red-400 font-bold">
                      ⚠ Exceeds Twitter character limit ({charCount - CHAR_LIMIT} chars over)
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer validation summary */}
      <div className="mt-2.5 flex items-center justify-between px-1 text-xs text-gray-400">
        <span>
          {isThread ? `Thread with ${tweets.length} posts` : 'Single post'}
        </span>
        <span className="rounded-full bg-gray-900 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400 border border-gray-800">
          ✓ X Format Ready
        </span>
      </div>
    </div>
  )
}
