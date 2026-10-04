"""ContentIR -> .docx via python-docx.

Uses Word's own built-in styles rather than hand-rolled formatting, so the
result opens looking like a normal document and stays editable downstream.
"""

from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.schemas.content_ir import ContentIR, Node
from app.services.rendering.srt import estimate_seconds

SEVERITY_LABEL = {
    "info": "Information",
    "low": "Low severity",
    "medium": "Medium severity",
    "high": "High severity",
    "critical": "Critical severity",
}
SEVERITY_RGB = {
    "critical": RGBColor(0xB4, 0x1C, 0x1C),
    "high": RGBColor(0xC2, 0x41, 0x0C),
    "medium": RGBColor(0xB4, 0x53, 0x09),
    "low": RGBColor(0x1D, 0x4E, 0xD8),
    "info": RGBColor(0x4A, 0x54, 0x68),
}


def _add_callout(doc: Document, node: Node) -> None:
    label = SEVERITY_LABEL.get(node.severity or "", node.severity or "Note")
    para = doc.add_paragraph(style="Intense Quote")
    run = para.add_run(node.title or label)
    run.bold = True
    run.font.color.rgb = SEVERITY_RGB.get(node.severity or "info", SEVERITY_RGB["info"])
    if node.text:
        para.add_run(f"\n{node.text}")


def _add_table(doc: Document, node: Node) -> None:
    rows = node.rows or []
    if not rows:
        return
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    for r, row in enumerate(rows):
        for c in range(width):
            cell = table.cell(r, c)
            cell.text = row[c] if c < len(row) else ""
            if r == 0:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True


def _add_labelled(doc: Document, label: str, body: str) -> None:
    para = doc.add_paragraph()
    para.add_run(f"{label}: ").bold = True
    para.add_run(body)


def _add_node(doc: Document, node: Node) -> None:
    match node.kind:
        case "heading":
            level = min(max(node.level or 2, 1), 4)
            doc.add_heading(node.text or node.title or "", level=level)
        case "paragraph":
            if node.text:
                doc.add_paragraph(node.text)
        case "quote":
            if node.text:
                doc.add_paragraph(node.text, style="Quote")
        case "bullets":
            if node.title:
                doc.add_paragraph().add_run(node.title).bold = True
            for item in node.items or []:
                doc.add_paragraph(item, style="List Bullet")
        case "post":
            if node.items:
                for item in node.items:
                    if item:
                        doc.add_paragraph(item)
            elif node.text:
                doc.add_paragraph(node.text)
        case "callout":
            _add_callout(doc, node)
        case "table":
            _add_table(doc, node)
        case "panel":
            doc.add_heading(node.title or "Panel", level=2)
            for item in node.items or []:
                doc.add_paragraph(item, style="List Bullet").runs[0].bold = True
            if node.text:
                doc.add_paragraph(node.text)
            if node.notes:
                _add_labelled(doc, "Visual", node.notes)
        case "scene":
            seconds = estimate_seconds(node.text or "")
            title = node.title or "Scene"
            doc.add_heading(f"{title} (~{round(seconds)} s)" if seconds else title, level=2)
            if node.text:
                _add_labelled(doc, "Narration", node.text)
            if node.items:
                _add_labelled(doc, "On-screen text", " · ".join(node.items))
            if node.notes:
                _add_labelled(doc, "Visuals", node.notes)
        case "slide":
            doc.add_heading(node.title or "Slide", level=3)
            for item in node.items or []:
                doc.add_paragraph(item, style="List Bullet")
            if node.notes:
                note = doc.add_paragraph(node.notes)
                note.runs[0].italic = True


def render(
    ir: ContentIR,
    *,
    include_citations: bool = False,
    citations: dict[str, str] | None = None,
    **_: object,
) -> bytes:
    doc = Document()
    doc.add_heading(ir.title, level=0)

    for node in ir.nodes:
        _add_node(doc, node)

    if include_citations:
        _add_citation_appendix(doc, ir, citations or {})

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _add_citation_appendix(doc: Document, ir: ContentIR, citations: dict[str, str]) -> None:
    """An official document should be able to show its own working."""
    used = [fid for node in ir.nodes for fid in node.fact_ids]
    if not used:
        return
    doc.add_page_break()
    doc.add_heading("Sources", level=1)
    intro = doc.add_paragraph("Every statement in this document is traceable to the source below.")
    intro.alignment = WD_ALIGN_PARAGRAPH.LEFT
    intro.runs[0].font.size = Pt(9)

    seen: set[str] = set()
    for fid in used:
        if fid in seen:
            continue
        seen.add(fid)
        doc.add_paragraph(citations.get(fid, fid), style="List Bullet")
