"""ContentIR -> .pptx via python-pptx.

Slides are drawn explicitly rather than filled into a designed .potx template.
A template would be a binary asset nobody in the repo can edit or diff; drawing
in code keeps the deck's look reviewable, versionable and consistent, and gives
exact control over spacing that placeholder autofit does not.
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.schemas.content_ir import ContentIR, Node

# A restrained palette that reads as official rather than corporate.
INK = RGBColor(0x17, 0x1B, 0x24)
MUTED = RGBColor(0x6B, 0x74, 0x86)
ACCENT = RGBColor(0x1D, 0x4E, 0xD8)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)

SEVERITY_ACCENT = {
    "critical": RGBColor(0xB4, 0x1C, 0x1C),
    "high": RGBColor(0xC2, 0x41, 0x0C),
    "medium": RGBColor(0xB4, 0x53, 0x09),
    "low": ACCENT,
    "info": MUTED,
}

SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)
BLANK_LAYOUT = 6

ACCENT_BAR_W = Inches(1.6)
ACCENT_BAR_W_TITLE = Inches(2.4)

MAX_BULLETS = 7
BULLET_CHARS_BEFORE_SHRINK = 90


def _blank(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[BLANK_LAYOUT])
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = PAPER
    return slide


def _accent_bar(slide, color: RGBColor = ACCENT, width=ACCENT_BAR_W) -> None:
    bar = slide.shapes.add_shape(1, MARGIN, Inches(0.62), width, Pt(4))
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False


def _textbox(slide, left, top, width, height):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.TOP
    return frame


def _footer(slide, source_name: str, page: int, total: int) -> None:
    frame = _textbox(slide, MARGIN, SLIDE_H - Inches(0.62), SLIDE_W - 2 * MARGIN, Inches(0.3))
    para = frame.paragraphs[0]
    run = para.add_run()
    run.text = f"{source_name}    |    {page} / {total}"
    run.font.size = Pt(10)
    run.font.color.rgb = MUTED


def _title_slide(prs: Presentation, ir: ContentIR, source_name: str) -> None:
    slide = _blank(prs)
    _accent_bar(slide, width=ACCENT_BAR_W_TITLE)

    frame = _textbox(slide, MARGIN, Inches(2.3), SLIDE_W - 2 * MARGIN, Inches(2.2))
    para = frame.paragraphs[0]
    para.alignment = PP_ALIGN.LEFT
    run = para.add_run()
    run.text = ir.title
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = INK

    sub = _textbox(slide, MARGIN, Inches(4.4), SLIDE_W - 2 * MARGIN, Inches(0.6))
    run = sub.paragraphs[0].add_run()
    run.text = f"Source: {source_name}"
    run.font.size = Pt(15)
    run.font.color.rgb = MUTED


def _content_slide(prs: Presentation, node: Node, source_name: str, page: int, total: int) -> None:
    slide = _blank(prs)
    accent = SEVERITY_ACCENT.get(node.severity or "", ACCENT)
    _accent_bar(slide, accent)

    title_frame = _textbox(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(1.0))
    run = title_frame.paragraphs[0].add_run()
    run.text = node.title or node.text or "Slide"
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = INK

    items = [i for i in (node.items or []) if i.strip()][:MAX_BULLETS]
    if items:
        body = _textbox(slide, MARGIN, Inches(2.05), SLIDE_W - 2 * MARGIN, Inches(4.4))
        longest = max(len(i) for i in items)
        size = Pt(18) if longest > BULLET_CHARS_BEFORE_SHRINK or len(items) > 5 else Pt(21)

        for index, item in enumerate(items):
            para = body.paragraphs[0] if index == 0 else body.add_paragraph()
            para.space_after = Pt(14)
            bullet = para.add_run()
            bullet.text = "—  "
            bullet.font.size = size
            bullet.font.color.rgb = accent
            run = para.add_run()
            run.text = item
            run.font.size = size
            run.font.color.rgb = INK

    if node.notes:
        slide.notes_slide.notes_text_frame.text = node.notes

    _footer(slide, source_name, page, total)


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


def render(ir: ContentIR, *, source_name: str = "", **_: object) -> bytes:
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    label = source_name or ir.title
    _title_slide(prs, ir, label)

    slides = _as_slides(ir)
    for index, node in enumerate(slides, start=1):
        _content_slide(prs, node, label, index, len(slides))

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
