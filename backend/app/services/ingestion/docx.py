"""DOCX -> blocks. Headings come from paragraph styles, which is more reliable
than the font heuristics a PDF forces on us.

Word has no fixed pagination, so every block reports page 1 and carries no
bbox; the viewer falls back to a structured text view for these.
"""

from __future__ import annotations

import io

from docx import Document as DocxDocument
from docx.document import Document as DocxDocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.ingestion.base import (
    ParsedBlock,
    ParsedDocument,
    SectionStack,
    classify,
    normalize_text,
)


def _iter_body(doc: DocxDocumentType):
    """Yield paragraphs and tables in document order (python-docx won't)."""
    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            yield Paragraph(child, doc)
        elif tag == "tbl":
            yield Table(child, doc)


def _heading_level(style_name: str) -> int | None:
    name = (style_name or "").strip().lower()
    if name == "title":
        return 1
    if name.startswith("heading"):
        tail = name.removeprefix("heading").strip()
        return int(tail) if tail.isdigit() else 1
    return None


def _table_to_text(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = [normalize_text(c.text) for c in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def parse(data: bytes) -> ParsedDocument:
    doc = DocxDocument(io.BytesIO(data))
    sections = SectionStack()
    blocks: list[ParsedBlock] = []
    order = 0

    for item in _iter_body(doc):
        if isinstance(item, Table):
            text = _table_to_text(item)
            block_type = "table"
            is_heading = False
        else:
            text = normalize_text(item.text)
            level = _heading_level(item.style.name if item.style else "")
            is_heading = level is not None and bool(text)
            if is_heading:
                sections.push(text, level or 1)
            block_type = classify(text, is_heading)

        if not text:
            continue

        blocks.append(
            ParsedBlock(
                page_no=1,
                section_path=sections.path,
                order_idx=order,
                block_type=block_type,
                text=text,
            )
        )
        order += 1

    return ParsedDocument(blocks=blocks, page_count=1)
