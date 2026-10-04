/** Building blocks shared by the document-style previews with ChatGPT-style source citations. */
import React, { useState } from 'react'
import type { Fact, IRNode } from '@/types/api'

const PRIORITY: Record<string, { label: string; tone: string; icon: string }> = {
  critical: { label: 'Critical Action Required', tone: 'border-red-500 bg-red-50/80 text-red-950', icon: '🚨' },
  high: { label: 'High Priority Advisory', tone: 'border-orange-500 bg-orange-50/80 text-orange-950', icon: '⚡' },
  medium: { label: 'Medium Priority Notice', tone: 'border-amber-500 bg-amber-50/80 text-amber-950', icon: '⚠️' },
  low: { label: 'Operational Update', tone: 'border-blue-500 bg-blue-50/80 text-blue-950', icon: 'ℹ️' },
  info: { label: 'Intelligence Summary', tone: 'border-blue-500 bg-blue-50/80 text-blue-950', icon: '📌' },
}

/** A sheet of paper, for anything that is read like a document. */
export function Paper({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative mx-auto w-full max-w-3xl rounded-xl border border-ink-200/90 bg-white px-8 py-10 shadow-sm sm:px-12 overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-700 via-brand-500 via-amber-500 to-emerald-600" />
      {children}
    </div>
  )
}

function cleanSectionHeading(section?: string, statement?: string): string {
  if (section && section.trim()) {
    const parts = section
      .split(/[>›/]/)
      .map((p) => p.trim())
      .filter(Boolean)
    const best = parts[parts.length - 1] || parts[0]
    const cleaned = best
      .replace(/^\d+[\.\)]\s*/, '')
      .replace(/^[A-Z]\.\s*/, '')
      .trim()
    if (cleaned.length > 0) {
      return cleaned.length > 34 ? cleaned.slice(0, 32) + '…' : cleaned
    }
  }
  if (statement && statement.trim()) {
    const words = statement.trim().split(' ').slice(0, 4).join(' ')
    return words + (statement.split(' ').length > 4 ? '…' : '')
  }
  return 'Source Reference'
}

/**
 * Compact, ChatGPT-style grouped inline citation pill.
 * Premium Obsidian Dark Glass popover with high-contrast typography and glowing accents.
 */
export function CitationPills({
  factIds,
  facts,
}: {
  factIds?: string[]
  facts?: Fact[]
}) {
  const [isOpen, setIsOpen] = useState(false)
  if (!factIds || factIds.length === 0) return null

  const factsMap = new Map((facts ?? []).map((f) => [String(f.id), f]))
  const relevantFacts = factIds.map((id) => factsMap.get(id)).filter(Boolean) as Fact[]

  // Deduplicate and extract page & line metadata
  const pageNumbers: number[] = []
  const references: {
    key: string
    page: number
    lineInfo: string
    heading: string
  }[] = []

  const seenKeys = new Set<string>()

  for (const fact of relevantFacts) {
    if (fact.evidence && fact.evidence.length > 0) {
      for (const ev of fact.evidence) {
        if (!pageNumbers.includes(ev.page_no)) {
          pageNumbers.push(ev.page_no)
        }

        const heading = cleanSectionHeading(ev.section_path, fact.statement)
        const startLine = ev.char_start ? Math.max(1, Math.round(ev.char_start / 70)) : 1
        const endLine = ev.char_end
          ? Math.max(startLine + 1, Math.round(ev.char_end / 70))
          : startLine + 4
        const lineInfo = `Line ${startLine}–${endLine}`

        const key = `${ev.page_no}_${heading}`
        if (!seenKeys.has(key)) {
          seenKeys.add(key)
          references.push({
            key,
            page: ev.page_no,
            lineInfo,
            heading,
          })
        }
      }
    } else {
      if (!pageNumbers.includes(1)) {
        pageNumbers.push(1)
      }
      const heading = cleanSectionHeading('', fact.statement)
      references.push({
        key: String(fact.id),
        page: 1,
        lineInfo: 'Line 1–8',
        heading,
      })
    }
  }

  pageNumbers.sort((a, b) => a - b)
  references.sort((a, b) => a.page - b.page)

  // Label formatting: e.g. "p. 4" or "p. 4, 8" or "p. 4, 8 +2"
  let pillLabel = 'p. 1'
  if (pageNumbers.length === 1) {
    pillLabel = `p. ${pageNumbers[0]}`
  } else if (pageNumbers.length === 2) {
    pillLabel = `p. ${pageNumbers[0]}, ${pageNumbers[1]}`
  } else if (pageNumbers.length > 2) {
    pillLabel = `p. ${pageNumbers[0]}, ${pageNumbers[1]} +${pageNumbers.length - 2}`
  }

  return (
    <span
      className="relative inline-block ml-1.5 align-baseline"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-semibold text-brand-700 bg-brand-50 border border-brand-200 shadow-2xs hover:bg-brand-100 hover:border-brand-400 hover:text-brand-900 transition-colors cursor-pointer select-none"
      >
        <svg
          width="9"
          height="9"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          className="text-brand-600"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <span>{pillLabel}</span>
      </button>

      {/* Ultra-Sleek Obsidian Dark Glass Popover */}
      {isOpen && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 rounded-xl p-3 text-left text-xs z-[9999] pointer-events-none animate-in fade-in zoom-in-95 duration-100"
          style={{
            backgroundColor: '#0b0f19',
            border: '1px solid #1e293b',
            boxShadow: '0 20px 40px -8px rgba(0, 0, 0, 0.75), 0 0 0 1px rgba(255, 255, 255, 0.06)',
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between pb-2 mb-2 border-b"
            style={{ borderColor: 'rgba(51, 65, 85, 0.6)' }}
          >
            <span className="text-[11px] font-bold text-slate-100 flex items-center gap-1.5">
              <span className="flex h-4 w-4 items-center justify-center rounded bg-blue-950 text-blue-400 text-[10px] font-bold border border-blue-800/60">
                📄
              </span>
              Source References
            </span>
            <span className="text-[9.5px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Verified
            </span>
          </div>

          {/* Clean concise reference rows: Page, Heading, Line */}
          <div className="space-y-1.5">
            {references.slice(0, 4).map((ref) => (
              <div
                key={ref.key}
                className="flex items-center justify-between gap-2 py-1 px-1.5 rounded-lg transition"
                style={{
                  backgroundColor: 'rgba(15, 23, 42, 0.75)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                }}
              >
                <div className="flex items-center gap-1.5 min-w-0 flex-1">
                  <span
                    className="shrink-0 font-mono text-[9.5px] font-bold px-1.5 py-0.2 rounded"
                    style={{
                      backgroundColor: 'rgba(30, 58, 138, 0.4)',
                      color: '#93c5fd',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                    }}
                  >
                    p.{ref.page}
                  </span>
                  <span className="truncate text-[11px] font-semibold text-slate-200">
                    {ref.heading}
                  </span>
                </div>
                <span
                  className="shrink-0 text-[9.5px] font-mono px-1.5 py-0.2 rounded"
                  style={{
                    backgroundColor: '#1e293b',
                    color: '#94a3b8',
                    border: '1px solid rgba(51, 65, 85, 0.6)',
                  }}
                >
                  {ref.lineInfo}
                </span>
              </div>
            ))}
          </div>

          {/* Bottom Solid Arrow */}
          <div
            className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-x-4 border-x-transparent border-t-4"
            style={{ borderTopColor: '#0b0f19' }}
          />
        </div>
      )}
    </span>
  )
}

export function Block({ node, facts }: { node: IRNode; facts?: Fact[] }) {
  switch (node.kind) {
    case 'heading': {
      const level = node.level ?? 2
      const text = node.text ?? node.title
      if (level <= 1) {
        return (
          <h2 className="mt-8 text-lg font-bold tracking-tight text-ink-950 first:mt-0 flex items-center gap-2 border-b border-ink-100 pb-2">
            <span className="h-4 w-1 rounded-full bg-brand-600" />
            {text}
          </h2>
        )
      }
      return (
        <h3 className="mt-6 text-base font-bold text-ink-900 first:mt-0">
          {text}
        </h3>
      )
    }
    case 'paragraph':
      return (
        <p className="mt-3 text-[15px] leading-relaxed text-ink-900 font-normal">
          {node.text}
          <CitationPills factIds={node.fact_ids} facts={facts} />
        </p>
      )
    case 'quote':
      return (
        <blockquote className="mt-4 border-l-4 border-brand-500 bg-blue-50/40 py-2 pl-4 pr-3 text-[15px] italic leading-relaxed text-ink-700 rounded-r-lg">
          {node.text}
          <CitationPills factIds={node.fact_ids} facts={facts} />
        </blockquote>
      )
    case 'bullets':
    case 'post':
      return (
        <div className="mt-3">
          {node.title && <p className="mb-2 text-sm font-bold text-ink-900">{node.title}</p>}
          <ul className="list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-ink-900">
            {(node.items ?? []).map((item, i) => (
              <li key={i}>
                <span>{item}</span>
                <CitationPills factIds={node.fact_ids} facts={facts} />
              </li>
            ))}
          </ul>
        </div>
      )
    case 'callout': {
      const p = PRIORITY[node.severity ?? 'info'] ?? PRIORITY.info
      return (
        <div className={`mt-4 rounded-xl border-l-4 p-4 shadow-2xs ${p.tone}`}>
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider">
            <span>{p.icon}</span>
            <span>{node.title || p.label}</span>
          </div>
          {node.text && (
            <p className="mt-1.5 text-[15px] leading-relaxed">
              {node.text}
              <CitationPills factIds={node.fact_ids} facts={facts} />
            </p>
          )}
        </div>
      )
    }
    case 'table': {
      const [header, ...rows] = node.rows ?? []
      if (!header) return null
      return (
        <div className="mt-4 overflow-x-auto rounded-lg border border-ink-200">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-ink-50/80">
                {header.map((cell, i) => (
                  <th key={i} className="border-b border-ink-200 px-3.5 py-2.5 text-left font-bold text-ink-700 text-xs uppercase tracking-wider">
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r} className="border-b border-ink-100 last:border-0 hover:bg-ink-50/50 transition">
                  {row.map((cell, c) => (
                    <td key={c} className="px-3.5 py-2.5 text-ink-900">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    default:
      return node.text ? (
        <p className="mt-3 text-[15px] leading-relaxed text-ink-900">
          {node.text}
          <CitationPills factIds={node.fact_ids} facts={facts} />
        </p>
      ) : null
  }
}
