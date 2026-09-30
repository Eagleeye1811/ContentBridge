import type { BBox } from '@/types/api'

/**
 * Convert a bounding box in PDF points into percentage CSS offsets, so an
 * overlay stays aligned at any render DPI or container width.
 */
export function bboxToPercent(bbox: BBox): {
  left: string
  top: string
  width: string
  height: string
} {
  const { x0, y0, x1, y1, page_width, page_height } = bbox
  const w = page_width || 1
  const h = page_height || 1
  return {
    left: `${(x0 / w) * 100}%`,
    top: `${(y0 / h) * 100}%`,
    width: `${((x1 - x0) / w) * 100}%`,
    height: `${((y1 - y0) / h) * 100}%`,
  }
}
