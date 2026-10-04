"""ContentIR -> .pdf via PyMuPDF.

Renders 16:9 PDF slide presentations matching the PowerPoint visual themes and layouts.
"""

from __future__ import annotations

import io
import pymupdf

from app.schemas.content_ir import ContentIR, Node

# 16:9 widescreen dimensions in PDF points (960 x 540)
PAGE_W, PAGE_H = 960.0, 540.0
MARGIN = 48.0

THEMES = {
    "navy_white": {
        "paper": (1.0, 1.0, 1.0),
        "ink": (0.06, 0.09, 0.16),
        "accent": (0.15, 0.39, 0.92),
        "muted": (0.39, 0.45, 0.54),
        "card_bg": (0.97, 0.98, 0.99),
        "card_border": (0.88, 0.91, 0.94),
    },
    "minimal_monochrome": {
        "paper": (1.0, 1.0, 1.0),
        "ink": (0.09, 0.09, 0.10),
        "accent": (0.25, 0.25, 0.27),
        "muted": (0.44, 0.44, 0.48),
        "card_bg": (0.95, 0.95, 0.96),
        "card_border": (0.89, 0.89, 0.90),
    },
    "corporate_blue_grey": {
        "paper": (1.0, 1.0, 1.0),
        "ink": (0.06, 0.09, 0.16),
        "accent": (0.01, 0.52, 0.78),
        "muted": (0.28, 0.33, 0.41),
        "card_bg": (0.94, 0.96, 0.98),
        "card_border": (0.80, 0.84, 0.88),
    },
    "dark_charcoal_blue": {
        "paper": (0.06, 0.09, 0.16),
        "ink": (0.97, 0.98, 0.99),
        "accent": (0.22, 0.74, 0.97),
        "muted": (0.58, 0.64, 0.72),
        "card_bg": (0.12, 0.16, 0.23),
        "card_border": (0.20, 0.25, 0.33),
    },
}


def _get_theme(theme_name: str | None) -> dict[str, tuple[float, float, float]]:
    return THEMES.get(theme_name or "", THEMES["navy_white"])


def _blank_page(doc: pymupdf.Document, colors: dict[str, tuple[float, float, float]]):
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    rect = pymupdf.Rect(0, 0, PAGE_W, PAGE_H)
    page.draw_rect(rect, color=colors["paper"], fill=colors["paper"])
    return page


def _accent_bar(page: pymupdf.Page, colors: dict[str, tuple[float, float, float]], width=120.0):
    rect = pymupdf.Rect(MARGIN, 40.0, MARGIN + width, 44.0)
    page.draw_rect(rect, color=colors["accent"], fill=colors["accent"])


def _footer(page: pymupdf.Page, colors: dict[str, tuple[float, float, float]], source_name: str, page_no: int, total: int):
    text = f"{source_name}    |    Slide {page_no} of {total}"
    rect = pymupdf.Rect(MARGIN, PAGE_H - 40.0, PAGE_W - MARGIN, PAGE_H - 15.0)
    page.insert_textbox(rect, text, fontsize=10, color=colors["muted"])


def _as_slides(ir: ContentIR) -> list[Node]:
    slides: list[Node] = []
    for node in ir.nodes:
        if node.kind == "slide":
            slides.append(node)
        elif node.kind in {"heading", "bullets", "paragraph"}:
            slides.append(Node(id=node.id, kind="slide", title=node.title or node.text or "", items=node.items or []))
    return slides


def render(ir: ContentIR, *, source_name: str = "", theme: str = "navy_white", **_: object) -> bytes:
    doc = pymupdf.open()
    colors = _get_theme(theme)
    label = source_name or ir.title

    # Title Slide
    page1 = _blank_page(doc, colors)
    _accent_bar(page1, colors, width=180.0)
    rect_title = pymupdf.Rect(MARGIN, 160.0, PAGE_W - MARGIN, 320.0)
    page1.insert_textbox(rect_title, ir.title, fontsize=32, color=colors["ink"])
    rect_sub = pymupdf.Rect(MARGIN, 340.0, PAGE_W - MARGIN, 400.0)
    page1.insert_textbox(rect_sub, f"Source Document: {label}", fontsize=14, color=colors["muted"])

    slides = _as_slides(ir)
    total_slides = len(slides)

    for index, node in enumerate(slides, start=1):
        page = _blank_page(doc, colors)
        _accent_bar(page, colors)

        title = node.title or node.text or "Slide"
        rect_t = pymupdf.Rect(MARGIN, 65.0, PAGE_W - MARGIN, 120.0)
        page.insert_textbox(rect_t, title, fontsize=24, color=colors["ink"])

        items = [i for i in (node.items or []) if i.strip()][:7]
        if items:
            rect_b = pymupdf.Rect(MARGIN, 135.0, PAGE_W - MARGIN, 460.0)
            body_text = "\n\n".join(f"—  {item}" for item in items)
            fontsize = 16 if len(items) > 5 else 18
            page.insert_textbox(rect_b, body_text, fontsize=fontsize, color=colors["ink"])

        _footer(page, colors, label, index, total_slides)

    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()
