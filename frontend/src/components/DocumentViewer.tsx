import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { bboxToPercent } from '@/lib/geometry'
import type { Block, Doc } from '@/types/api'

interface Props {
  doc: Doc
  page: number
  blocks: Block[]
  selectedId: string | null
  onSelect: (id: string) => void
}

/**
 * Renders a rasterized page with every block's bounding box overlaid.
 * Boxes are positioned as percentages of the page, so they stay aligned at
 * any render DPI or container width.
 */
export default function DocumentViewer({ doc, page, blocks, selectedId, onSelect }: Props) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  // PDFs are rasterized page by page; an image source is its own single page.
  const hasGeometry = doc.mime === 'application/pdf' || doc.mime.startsWith('image/')

  useEffect(() => {
    if (!hasGeometry) return
    let revoked: string | null = null
    let cancelled = false
    setImageUrl(null)
    setError(null)

    api
      .pageImageUrl(doc.id, page)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        revoked = url
        setImageUrl(url)
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : 'Render failed'))

    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [doc.id, page, hasGeometry])

  if (!hasGeometry) {
    return (
      <div className="rounded-2xl border border-ink-200 bg-white p-6 text-sm text-ink-600">
        <p className="font-medium text-ink-900">No page preview for this file type</p>
        <p className="mt-1">
          The text is shown alongside, organised by section. Everything still links back to its
          place in the source.
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {error}
      </div>
    )
  }

  if (!imageUrl) {
    return (
      <div className="flex h-96 items-center justify-center rounded-xl border border-ink-200 bg-white text-sm text-ink-400">
        {doc.mime.startsWith('image/') ? 'Loading image…' : `Rendering page ${page}…`}
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-ink-200 bg-white shadow-sm">
      <img src={imageUrl} alt={`Page ${page}`} className="block w-full" />
      {blocks.map((b) => {
        if (!b.bbox) return null
        const selected = b.id === selectedId
        return (
          <button
            key={b.id}
            onClick={() => onSelect(b.id)}
            title={b.section_path}
            aria-label={b.text.slice(0, 80)}
            className={`absolute rounded-sm border transition ${
              selected
                ? 'border-amber-500 bg-amber-300/40 ring-2 ring-amber-400'
                : 'border-transparent hover:border-brand-500 hover:bg-brand-500/10'
            }`}
            style={bboxToPercent(b.bbox)}
          />
        )
      })}
    </div>
  )
}
