"""ContentIR -> .pptx via python-pptx.

Enhanced Presentation Studio Renderer:
Renders widescreen (16:9) presentations with customizable themes, safe margins,
overflow detection, source traceability, and rich visual layout renderers.

Supported Themes:
- navy_white (default)
- minimal_monochrome
- corporate_blue_grey
- dark_charcoal_blue

Supported Slide Layouts:
- title
- section_divider
- standard_bullet
- two_column
- process
- timeline
- metrics
- comparison
- image_caption
- table
- key_takeaways
- references
"""

from __future__ import annotations

import io
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.schemas.content_ir import ContentIR, Node

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)
BLANK_LAYOUT = 6

THEMES = {
    "corporate_blue": {
        "name": "Corporate Blue",
        "paper": RGBColor(0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x0F, 0x17, 0x2A),
        "accent": RGBColor(0x1E, 0x40, 0xAF),
        "accent_secondary": RGBColor(0x3B, 0x82, 0xF6),
        "muted": RGBColor(0x47, 0x55, 0x69),
        "card_bg": RGBColor(0xF8, 0xFA, 0xFC),
        "card_border": RGBColor(0xCB, 0xD5, 0xE1),
        "table_header_bg": RGBColor(0x1E, 0x40, 0xAF),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xF1, 0xF5, 0xF9),
    },
    "midnight_dark": {
        "name": "Midnight Dark",
        "paper": RGBColor(0x0F, 0x17, 0x2A),
        "ink": RGBColor(0xF8, 0xFA, 0xFC),
        "accent": RGBColor(0x38, 0xBD, 0xF8),
        "accent_secondary": RGBColor(0x81, 0x8C, 0xF8),
        "muted": RGBColor(0x94, 0xA3, 0xB8),
        "card_bg": RGBColor(0x1E, 0x29, 0x3B),
        "card_border": RGBColor(0x33, 0x41, 0x55),
        "table_header_bg": RGBColor(0x1E, 0x29, 0x3B),
        "table_header_text": RGBColor(0x38, 0xBD, 0xF8),
        "table_row_alt": RGBColor(0x11, 0x18, 0x27),
    },
    "minimal_monochrome": {
        "name": "Minimal Monochrome",
        "paper": RGBColor(0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x18, 0x18, 0x1B),
        "accent": RGBColor(0x3F, 0x3F, 0x46),
        "accent_secondary": RGBColor(0x71, 0x71, 0x7A),
        "muted": RGBColor(0x71, 0x71, 0x7A),
        "card_bg": RGBColor(0xF4, 0xF4, 0xF5),
        "card_border": RGBColor(0xE4, 0xE4, 0xE7),
        "table_header_bg": RGBColor(0x27, 0x27, 0x2A),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xFA, 0xFA, 0xFA),
    },
    "modern_gradient": {
        "name": "Modern Gradient",
        "paper": RGBColor(0xFA, 0xFA, 0xFD),
        "ink": RGBColor(0x1E, 0x1B, 0x4B),
        "accent": RGBColor(0x63, 0x66, 0xF1),
        "accent_secondary": RGBColor(0xA8, 0x55, 0xF7),
        "muted": RGBColor(0x64, 0x74, 0x8B),
        "card_bg": RGBColor(0xEE, 0xF2, 0xFF),
        "card_border": RGBColor(0xC7, 0xD2, 0xFE),
        "table_header_bg": RGBColor(0x4F, 0x46, 0xE5),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xF5, 0xF3, 0xFF),
    },
    "academic_research": {
        "name": "Academic Research",
        "paper": RGBColor(0xFD, 0xFB, 0xF7),
        "ink": RGBColor(0x1C, 0x19, 0x17),
        "accent": RGBColor(0x99, 0x1B, 0x1B),
        "accent_secondary": RGBColor(0xB4, 0x53, 0x09),
        "muted": RGBColor(0x57, 0x53, 0x4E),
        "card_bg": RGBColor(0xF5, 0xF5, 0xF4),
        "card_border": RGBColor(0xD6, 0xD3, 0xD1),
        "table_header_bg": RGBColor(0x78, 0x1D, 0x1D),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xFA, 0xFA, 0xF9),
    },
    "data_analytics": {
        "name": "Data & Analytics",
        "paper": RGBColor(0xFF, 0xFF, 0xFF),
        "ink": RGBColor(0x0F, 0x17, 0x2A),
        "accent": RGBColor(0x0D, 0x94, 0x88),
        "accent_secondary": RGBColor(0x02, 0x84, 0xC7),
        "muted": RGBColor(0x47, 0x55, 0x69),
        "card_bg": RGBColor(0xF0, 0xFD, 0xFA),
        "card_border": RGBColor(0x99, 0xF6, 0xE4),
        "table_header_bg": RGBColor(0x0D, 0x94, 0x88),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xCC, 0xFB, 0xF1),
    },
    "warm_editorial": {
        "name": "Warm Editorial",
        "paper": RGBColor(0xFB, 0xF9, 0xF5),
        "ink": RGBColor(0x29, 0x25, 0x24),
        "accent": RGBColor(0xC2, 0x41, 0x0C),
        "accent_secondary": RGBColor(0xD9, 0x77, 0x06),
        "muted": RGBColor(0x78, 0x71, 0x6C),
        "card_bg": RGBColor(0xF5, 0xF2, 0xEB),
        "card_border": RGBColor(0xE7, 0xE0, 0xD3),
        "table_header_bg": RGBColor(0x9A, 0x34, 0x12),
        "table_header_text": RGBColor(0xFF, 0xFF, 0xFF),
        "table_row_alt": RGBColor(0xFF, 0xED, 0xD5),
    },
    "high_contrast": {
        "name": "High-Contrast Presentation",
        "paper": RGBColor(0x00, 0x00, 0x00),
        "ink": RGBColor(0xFF, 0xFF, 0xFF),
        "accent": RGBColor(0xFA, 0xCC, 0x15),
        "accent_secondary": RGBColor(0x06, 0xB6, 0xD4),
        "muted": RGBColor(0xE2, 0xE8, 0xF0),
        "card_bg": RGBColor(0x18, 0x18, 0x1B),
        "card_border": RGBColor(0xFF, 0xFF, 0xFF),
        "table_header_bg": RGBColor(0xFA, 0xCC, 0x15),
        "table_header_text": RGBColor(0x00, 0x00, 0x00),
        "table_row_alt": RGBColor(0x27, 0x27, 0x2A),
    },
}

THEME_ALIASES = {
    "navy_white": "corporate_blue",
    "corporate_blue_grey": "corporate_blue",
    "dark_charcoal_blue": "midnight_dark",
    "dark_executive": "midnight_dark",
}


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    import re
    # Clean corrupt currency glyphs e.g. I4.80 crore -> ₹4.80 crore or INR 4.80 crore fallback
    cleaned = re.sub(r'\bI(?=\d+(?:\.\d+)?\s*(?:crore|lakh|million|billion|cr|l|k)\b)', '₹', text)
    cleaned = re.sub(r'\bI(?=\d+(?:\.\d+)?\b)', '₹', cleaned)
    return cleaned


def _get_theme(theme_name: str | None) -> dict[str, RGBColor]:
    key = theme_name or "corporate_blue"
    key = THEME_ALIASES.get(key, key)
    return THEMES.get(key, THEMES["corporate_blue"])


def _blank(prs: Presentation, colors: dict[str, RGBColor]):
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = colors["paper"]
    return slide


def _accent_bar(slide, colors: dict[str, RGBColor], width=Inches(1.6)) -> None:
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, Inches(0.62), width, Pt(4))
    bar.fill.solid()
    bar.fill.fore_color.rgb = colors["accent"]
    bar.line.fill.background()
    bar.shadow.inherit = False


def _textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    return frame


def _footer(slide, colors: dict[str, RGBColor], source_name: str, page: int, total: int, fact_ids: list[str] | None = None) -> None:
    frame = _textbox(slide, MARGIN, SLIDE_H - Inches(0.62), SLIDE_W - 2 * MARGIN, Inches(0.3))
    para = frame.paragraphs[0]
    run = para.add_run()
    citations_str = f"  |  Facts: {', '.join(fact_ids[:3])}" if fact_ids else ""
    run.text = f"{source_name}    |    Slide {page} of {total}{citations_str}"
    run.font.size = Pt(10)
    run.font.color.rgb = colors["muted"]


def _card(slide, left, top, width, height, colors: dict[str, RGBColor]):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = colors["card_bg"]
    shape.line.color.rgb = colors["card_border"]
    shape.line.width = Pt(1)
    return shape


def _compute_safe_font_size(items: list[str], max_allowed=20, min_allowed=13) -> Pt:
    """Dynamically compute font size to prevent text overflow outside bounding boxes."""
    if not items:
        return Pt(max_allowed)
    max_len = max(len(i) for i in items)
    count = len(items)

    if count > 6 or max_len > 120:
        return Pt(min_allowed)
    elif count > 4 or max_len > 80:
        return Pt(15)
    elif count > 3 or max_len > 50:
        return Pt(17)
    return Pt(max_allowed)


def _parse_metric_item(item: str) -> tuple[str, str]:
    """Extract figure and label/description cleanly without fallback to generic #1."""
    if ":" in item:
        parts = item.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    if " - " in item:
        parts = item.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    if " — " in item:
        parts = item.split(" — ", 1)
        return parts[0].strip(), parts[1].strip()
    
    words = item.split()
    if len(words) <= 3:
        return item, ""
    return " ".join(words[:2]), " ".join(words[2:])


def _parse_timeline_item(item: str) -> tuple[str, str]:
    """Extract timestamp and event description cleanly without fallback to Event N."""
    if ":" in item:
        parts = item.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    if " - " in item:
        parts = item.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    if " — " in item:
        parts = item.split(" — ", 1)
        return parts[0].strip(), parts[1].strip()

    words = item.split()
    if len(words) <= 4:
        return item, ""
    return " ".join(words[:3]), " ".join(words[3:])


# --------------------------------------------------------------------------
# Layout Renderers
# --------------------------------------------------------------------------


def _title_slide(prs: Presentation, ir: ContentIR, colors: dict[str, RGBColor], source_name: str) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors, width=Inches(2.5))

    frame = _textbox(slide, MARGIN, Inches(2.0), SLIDE_W - 2 * MARGIN, Inches(2.2))
    para = frame.paragraphs[0]
    run = para.add_run()
    run.text = ir.title
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    sub = _textbox(slide, MARGIN, Inches(4.3), SLIDE_W - 2 * MARGIN, Inches(1.0))
    p1 = sub.paragraphs[0]
    r1 = p1.add_run()
    r1.text = f"Source Document: {source_name}" if source_name else "AI Presentation Studio"
    r1.font.size = Pt(16)
    r1.font.bold = True
    r1.font.color.rgb = colors["muted"]

    p2 = sub.add_paragraph()
    p2.space_before = Pt(6)
    r2 = p2.add_run()
    r2.text = "Verified Source of Truth Briefing  |  Executive Synthesis"
    r2.font.size = Pt(13)
    r2.font.color.rgb = colors["muted"]


def _section_divider_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _card(slide, MARGIN, Inches(2.0), SLIDE_W - 2 * MARGIN, Inches(3.5), colors)

    frame = _textbox(slide, MARGIN + Inches(0.4), Inches(2.8), SLIDE_W - 2 * MARGIN - Inches(0.8), Inches(2.0))
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.CENTER
    run = para.add_run()
    run.text = node.title or node.text or "Section Divider"
    run.font.size = Pt(32)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _standard_bullet_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or node.text or "Slide"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    items = [i for i in (node.items or []) if i.strip()][:8]
    if items:
        body = _textbox(slide, MARGIN, Inches(2.1), SLIDE_W - 2 * MARGIN, Inches(4.4))
        size = _compute_safe_font_size(items, max_allowed=20, min_allowed=13)

        for index, item in enumerate(items):
            para = body.paragraphs[0] if index == 0 else body.add_paragraph()
            para.space_after = Pt(10)
            bullet = para.add_run()
            bullet.text = "—  "
            bullet.font.size = size
            bullet.font.color.rgb = colors["accent"]
            run = para.add_run()
            run.text = item
            run.font.size = size
            run.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _two_column_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Key Analysis"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    items = [i for i in (node.items or []) if i.strip()]
    mid = (len(items) + 1) // 2
    left_items, right_items = items[:mid], items[mid:]

    col_w = (SLIDE_W - 2 * MARGIN - Inches(0.4)) / 2

    # Left Card
    _card(slide, MARGIN, Inches(2.0), col_w, Inches(4.5), colors)
    frame_left = _textbox(slide, MARGIN + Inches(0.3), Inches(2.2), col_w - Inches(0.6), Inches(4.1))
    size_left = _compute_safe_font_size(left_items, max_allowed=17, min_allowed=13)
    for idx, item in enumerate(left_items):
        p = frame_left.paragraphs[0] if idx == 0 else frame_left.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"•  {item}"
        r.font.size = size_left
        r.font.color.rgb = colors["ink"]

    # Right Card
    right_left = MARGIN + col_w + Inches(0.4)
    _card(slide, right_left, Inches(2.0), col_w, Inches(4.5), colors)
    frame_right = _textbox(slide, right_left + Inches(0.3), Inches(2.2), col_w - Inches(0.6), Inches(4.1))
    size_right = _compute_safe_font_size(right_items, max_allowed=17, min_allowed=13)
    for idx, item in enumerate(right_items):
        p = frame_right.paragraphs[0] if idx == 0 else frame_right.add_paragraph()
        p.space_after = Pt(8)
        r = p.add_run()
        r.text = f"•  {item}"
        r.font.size = size_right
        r.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _timeline_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    """Timeline layout keeping timestamps and event descriptions grouped cleanly."""
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Timeline & Milestones"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    # Horizontal Timeline Line
    line_y = Inches(4.2)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, MARGIN, line_y, SLIDE_W - 2 * MARGIN, Pt(4))
    line.fill.solid()
    line.fill.fore_color.rgb = colors["accent"]
    line.line.fill.background()

    items = [i for i in (node.items or []) if i.strip()][:4]
    count = max(1, len(items))
    gap = Inches(0.3)
    card_w = (SLIDE_W - 2 * MARGIN - (gap * (count - 1))) / count

    for idx, item in enumerate(items):
        left = MARGIN + idx * (card_w + gap)
        # Alternate above and below line
        top = Inches(2.2) if idx % 2 == 0 else Inches(4.5)
        _card(slide, left, top, card_w, Inches(1.8), colors)

        ts, desc = _parse_timeline_item(item)

        frame = _textbox(slide, left + Inches(0.2), top + Inches(0.2), card_w - Inches(0.4), Inches(1.4))
        p1 = frame.paragraphs[0]
        r1 = p1.add_run()
        r1.text = ts
        r1.font.size = Pt(13)
        r1.font.bold = True
        r1.font.color.rgb = colors["accent"]

        p2 = frame.add_paragraph()
        p2.space_before = Pt(4)
        r2 = p2.add_run()
        r2.text = desc
        r2.font.size = Pt(12)
        r2.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _process_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Process Flow"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    items = [i for i in (node.items or []) if i.strip()][:4]
    count = max(1, len(items))
    gap = Inches(0.3)
    card_w = (SLIDE_W - 2 * MARGIN - (gap * (count - 1))) / count
    hdr_text_color = colors.get("table_header_text", RGBColor(0xFF, 0xFF, 0xFF))

    for idx, item in enumerate(items):
        left = MARGIN + idx * (card_w + gap)
        _card(slide, left, Inches(2.3), card_w, Inches(4.0), colors)

        # Step Number Badge
        badge = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(0.3), Inches(2.6), Inches(0.5), Inches(0.5))
        badge.fill.solid()
        badge.fill.fore_color.rgb = colors["accent"]
        badge.line.fill.background()
        tf = badge.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = str(idx + 1)
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = hdr_text_color

        # Step Text
        frame = _textbox(slide, left + Inches(0.3), Inches(3.3), card_w - Inches(0.6), Inches(2.8))
        p = frame.paragraphs[0]
        r = p.add_run()
        r.text = item
        r.font.size = Pt(14) if len(item) > 60 else Pt(16)
        r.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _metrics_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Key Metrics & Impact"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    items = [i for i in (node.items or []) if i.strip()][:4]
    count = max(1, len(items))
    gap = Inches(0.4)
    card_w = (SLIDE_W - 2 * MARGIN - (gap * (count - 1))) / count

    for idx, item in enumerate(items):
        left = MARGIN + idx * (card_w + gap)
        _card(slide, left, Inches(2.4), card_w, Inches(3.8), colors)

        fig, desc = _parse_metric_item(item)

        frame = _textbox(slide, left + Inches(0.2), Inches(2.7), card_w - Inches(0.4), Inches(3.2))

        # Figure
        p1 = frame.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        r1 = p1.add_run()
        r1.text = fig[:20]
        r1.font.size = Pt(28) if len(fig) > 10 else Pt(32)
        r1.font.bold = True
        r1.font.color.rgb = colors["accent"]

        # Description
        p2 = frame.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(10)
        r2 = p2.add_run()
        r2.text = desc
        r2.font.size = Pt(14)
        r2.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _table_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Data Table"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    rows = node.rows or []
    if not rows and node.items:
        rows = [["Item", "Details"]] + [[f"Point {i+1}", item] for i, item in enumerate(node.items)]

    if rows:
        num_rows = min(8, len(rows))
        num_cols = max(1, min(5, len(rows[0])))
        table_w = SLIDE_W - 2 * MARGIN
        table_h = Inches(0.45 * num_rows)

        table_shape = slide.shapes.add_table(num_rows, num_cols, MARGIN, Inches(2.2), table_w, table_h)
        table = table_shape.table

        hdr_bg = colors.get("table_header_bg", colors["accent"])
        hdr_fg = colors.get("table_header_text", RGBColor(0xFF, 0xFF, 0xFF))
        row_alt = colors.get("table_row_alt", colors["card_bg"])

        for r_idx in range(num_rows):
            for c_idx in range(num_cols):
                val = rows[r_idx][c_idx] if c_idx < len(rows[r_idx]) else ""
                cell = table.cell(r_idx, c_idx)
                cell.text = str(val)
                p = cell.text_frame.paragraphs[0]
                p.font.size = Pt(13)
                if r_idx == 0:
                    p.font.bold = True
                    p.font.color.rgb = hdr_fg
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = hdr_bg
                else:
                    p.font.color.rgb = colors["ink"]
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = row_alt if r_idx % 2 == 1 else colors["card_bg"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _key_takeaways_slide(
    prs: Presentation, node: Node, colors: dict[str, RGBColor], source_name: str, page: int, total: int
) -> None:
    """Summary of key takeaways slide layout."""
    slide = _blank(prs, colors)
    _accent_bar(slide, colors)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or "Key Takeaways & Action Plan"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = colors["ink"]

    items = [i for i in (node.items or []) if i.strip()][:3]
    count = max(1, len(items))
    card_h = Inches(4.2 / count)

    for idx, item in enumerate(items):
        top = Inches(2.1) + idx * (card_h + Inches(0.2))
        _card(slide, MARGIN, top, SLIDE_W - 2 * MARGIN, card_h, colors)

        frame = _textbox(slide, MARGIN + Inches(0.4), top + Inches(0.2), SLIDE_W - 2 * MARGIN - Inches(0.8), card_h - Inches(0.4))
        p = frame.paragraphs[0]
        r1 = p.add_run()
        r1.text = f"Takeaway {idx + 1}: "
        r1.font.bold = True
        r1.font.size = Pt(16)
        r1.font.color.rgb = colors["accent"]

        r2 = p.add_run()
        r2.text = item
        r2.font.size = Pt(15)
        r2.font.color.rgb = colors["ink"]

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, colors, source_name, page, total, node.fact_ids)


def _as_slides(ir: ContentIR) -> list[Node]:
    """Fold non-slide nodes into slides so any ContentIR can become a deck."""
    slides: list[Node] = []
    for node in ir.nodes:
        if node.kind == "slide":
            slides.append(node)
        elif node.kind == "heading":
            slides.append(
                Node(
                    id=node.id,
                    kind="slide",
                    title=node.text or node.title,
                    items=[],
                    fact_ids=node.fact_ids,
                )
            )
        elif node.kind in {"bullets", "post"}:
            if slides and not slides[-1].items:
                slides[-1] = slides[-1].model_copy(update={"items": list(node.items or [])})
            else:
                slides.append(
                    Node(
                        id=node.id,
                        kind="slide",
                        title="",
                        items=list(node.items or []),
                        fact_ids=node.fact_ids,
                    )
                )
        elif node.kind in {"panel", "scene"}:
            body = list(node.items or []) if node.kind == "panel" else [node.text or ""]
            slides.append(
                Node(
                    id=node.id,
                    kind="slide",
                    title=node.title or "",
                    items=[b for b in body if b],
                    notes=node.notes,
                    fact_ids=node.fact_ids,
                )
            )
        elif node.kind in {"paragraph", "quote", "callout"} and node.text:
            slides.append(
                Node(
                    id=node.id,
                    kind="slide",
                    title=node.title or "",
                    items=[node.text],
                    severity=node.severity,
                    fact_ids=node.fact_ids,
                )
            )
    return slides


def render(ir: ContentIR, *, source_name: str = "", theme: str = "corporate_blue", **_: object) -> bytes:
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    colors = _get_theme(theme)
    label = source_name or ir.title

    _title_slide(prs, ir, colors, label)

    slides = _as_slides(ir)
    total_slides = len(slides) + 1  # Total physical slides includes physical cover slide

    for index, node in enumerate(slides, start=2):
        layout = (node.layout or "standard_bullet").lower()

        if layout == "section_divider":
            _section_divider_slide(prs, node, colors, label, index, total_slides)
        elif layout in {"two_column", "comparison"}:
            _two_column_slide(prs, node, colors, label, index, total_slides)
        elif layout == "timeline":
            _timeline_slide(prs, node, colors, label, index, total_slides)
        elif layout in {"process", "roadmap"}:
            _process_slide(prs, node, colors, label, index, total_slides)
        elif layout in {"metrics"}:
            _metrics_slide(prs, node, colors, label, index, total_slides)
        elif layout in {"key_takeaways", "takeaway"}:
            _key_takeaways_slide(prs, node, colors, label, index, total_slides)
        elif layout == "table" or node.rows:
            _table_slide(prs, node, colors, label, index, total_slides)
        else:
            _standard_bullet_slide(prs, node, colors, label, index, total_slides)

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
