/**
 * Everyday wording for the values the backend stores. The UI never shows a
 * raw key, a status code or a model term to the user.
 */
import type { Output, VerdictKind } from '@/types/api'

const FORMAT_LABELS: Record<string, string> = {
  advisory: 'Advisory',
  ppt: 'Presentation',
  summary: 'Executive Summary',
  email: 'Official Email',
  linkedin: 'LinkedIn Post',
  social: 'LinkedIn Post',
  twitter: 'Twitter/X Post',
  press_release: 'Press Release',
  report: 'Report',
  infographic: 'Infographic',
  video: 'Video',
}

export function formatLabel(key: string): string {
  return FORMAT_LABELS[key] ?? key.replace(/_/g, ' ')
}

export function controlLabel(key: string | undefined): string {
  if (!key) return ''
  const spaced = key.replace(/_/g, ' ')
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export const LANGUAGE_LABELS: Record<string, string> = {
  en: 'English',
  hi: 'Hindi',
  mr: 'Marathi',
}

export function languageLabel(code: string): string {
  return LANGUAGE_LABELS[code] ?? code
}

type Tone = 'neutral' | 'info' | 'good' | 'warn' | 'bad'

export const STATUS: Record<Output['status'], { label: string; tone: Tone }> = {
  draft: { label: 'Draft', tone: 'neutral' },
  verified: { label: 'Checked', tone: 'info' },
  in_review: { label: 'Waiting for approval', tone: 'warn' },
  approved: { label: 'Approved', tone: 'good' },
  rejected: { label: 'Changes requested', tone: 'bad' },
  exported: { label: 'Downloaded', tone: 'good' },
}

export function statusOf(status: string): { label: string; tone: Tone } {
  return STATUS[status as Output['status']] ?? { label: controlLabel(status), tone: 'neutral' }
}

export const VERDICT: Record<VerdictKind, { label: string; tone: Tone }> = {
  supported: { label: 'Matches the source', tone: 'good' },
  partial: { label: 'Partly matches', tone: 'warn' },
  unsupported: { label: 'Not found in the source', tone: 'neutral' },
  contradicted: { label: 'Conflicts with the source', tone: 'bad' },
}

export const TONE_CLASS: Record<Tone, string> = {
  neutral: 'bg-ink-100 text-ink-600',
  info: 'bg-blue-50 text-brand-600',
  good: 'bg-emerald-50 text-emerald-700',
  warn: 'bg-amber-50 text-amber-700',
  bad: 'bg-red-50 text-red-700',
}

export function accuracyTone(score: number): Tone {
  return score >= 0.85 ? 'good' : score >= 0.6 ? 'warn' : 'bad'
}

export function sourceKind(mime: string): string {
  if (mime.startsWith('image/')) return 'Image'
  if (mime.startsWith('text/')) return 'Text'
  if (mime === 'application/pdf') return 'PDF'
  if (mime.includes('wordprocessing')) return 'Word'
  if (mime.includes('presentation')) return 'PowerPoint'
  return 'File'
}

export const DOC_STATUS: Record<string, { label: string; tone: Tone }> = {
  uploaded: { label: 'Uploading', tone: 'neutral' },
  parsing: { label: 'Reading', tone: 'neutral' },
  parsed: { label: 'Reading', tone: 'neutral' },
  indexing: { label: 'Reading', tone: 'neutral' },
  indexed: { label: 'Needs key facts', tone: 'warn' },
  extracting: { label: 'Finding key facts', tone: 'neutral' },
  ready: { label: 'Ready', tone: 'good' },
  failed: { label: 'Failed', tone: 'bad' },
}

export function timeAgo(iso: string): string {
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`
  return new Date(iso).toLocaleDateString()
}
