"""PDF -> blocks, with page, section and bounding box preserved.

Heading detection is font-size based: the most common size (weighted by
characters) is the body text, and anything meaningfully larger is a heading.
Heading sizes are ranked to give nesting levels.
"""

from __future__ import annotations

from collections import Counter

import pymupdf

from app.services.ingestion.base import (
    ParsedBlock,
    ParsedDocument,
    SectionStack,
    classify,
    normalize_text,
)

HEADING_SIZE_DELTA = 0.6  # points above body size before we call it a heading
MAX_HEADING_LEVELS = 3
BOLD_FLAG = 1 << 4  # PyMuPDF span flag bit for bold


def _body_font_size(doc: pymupdf.Document) -> float:
    """Most common font size weighted by how many characters use it."""
    weights: Counter[float] = Counter()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        weights[round(span["size"], 1)] += len(text)
    return weights.most_common(1)[0][0] if weights else 11.0


def _heading_levels(doc: pymupdf.Document, body_size: float) -> dict[float, int]:
    sizes = set()
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    size = round(span["size"], 1)
                    if span["text"].strip() and size > body_size + HEADING_SIZE_DELTA:
                        sizes.add(size)
    ranked = sorted(sizes, reverse=True)[:MAX_HEADING_LEVELS]
    return {size: level for level, size in enumerate(ranked, start=1)}


def _block_text_and_style(block: dict) -> tuple[str, float, bool]:
    """Flatten a PyMuPDF block into text plus its dominant size and boldness."""
    parts: list[str] = []
    max_size = 0.0
    bold_chars = 0
    total_chars = 0
    for line in block["lines"]:
        line_parts = []
        for span in line["spans"]:
            text = span["text"]
            if not text.strip():
                continue
            line_parts.append(text)
            max_size = max(max_size, round(span["size"], 1))
            n = len(text.strip())
            total_chars += n
            if span.get("flags", 0) & BOLD_FLAG:
                bold_chars += n
        if line_parts:
            parts.append("".join(line_parts))
    text = normalize_text(" ".join(parts))
    is_bold = total_chars > 0 and bold_chars / total_chars > 0.6
    return text, max_size, is_bold


def parse(data: bytes) -> ParsedDocument:
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        body_size = _body_font_size(doc)
        levels = _heading_levels(doc, body_size)
        fallback_level = (max(levels.values()) + 1) if levels else 1

        sections = SectionStack()
        blocks: list[ParsedBlock] = []
        order = 0

        for page_index, page in enumerate(doc, start=1):
            page_w, page_h = page.rect.width, page.rect.height
            raw_blocks = page.get_text("dict")["blocks"]
            # Reading order: top to bottom, then left to right.
            raw_blocks.sort(key=lambda b: (round(b["bbox"][1], 1), round(b["bbox"][0], 1)))

            for raw in raw_blocks:
                if raw.get("type") != 0:  # 0 = text; images carry no claims
                    continue
                text, size, is_bold = _block_text_and_style(raw)
                if not text:
                    continue

                # A short bold line that isn't a sentence reads as a heading even
                # when its font size matches the body text.
                is_heading = size in levels or (
                    is_bold and len(text) <= 80 and not text.endswith((".", ";", ":"))
                )
                if is_heading:
                    sections.push(text, levels.get(size, fallback_level))

                x0, y0, x1, y1 = raw["bbox"]
                blocks.append(
                    ParsedBlock(
                        page_no=page_index,
                        section_path=sections.path,
                        order_idx=order,
                        block_type=classify(text, is_heading),
                        text=text,
                        bbox={
                            "x0": round(x0, 2),
                            "y0": round(y0, 2),
                            "x1": round(x1, 2),
                            "y1": round(y1, 2),
                            "page_width": round(page_w, 2),
                            "page_height": round(page_h, 2),
                        },
                    )
                )
                order += 1

        return ParsedDocument(blocks=blocks, page_count=doc.page_count)
    finally:
        doc.close()


def render_page_png(data: bytes, page_no: int, dpi: int = 110) -> bytes:
    """Rasterize one page for the traceability viewer."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        if not 1 <= page_no <= doc.page_count:
            raise IndexError(f"Page {page_no} out of range (1..{doc.page_count})")
        pix = doc[page_no - 1].get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()
