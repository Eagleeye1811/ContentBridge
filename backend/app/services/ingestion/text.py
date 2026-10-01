"""Plain text / Markdown -> blocks.

Covers pasted text as well as .txt and .md files. Paragraphs are separated by
blank lines. Headings come from Markdown `#` markers or, in plain text, from a
short standalone line with no closing punctuation. Like DOCX there is no page
geometry, so every block is page 1 with no bbox; the section path still makes
each block citable.
"""

from __future__ import annotations

import re

from app.services.ingestion.base import (
    LIST_PREFIX,
    ParsedBlock,
    ParsedDocument,
    SectionStack,
    classify,
    normalize_text,
)

MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
MAX_HEADING_CHARS = 80
MAX_HEADING_WORDS = 12


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _looks_like_heading(line: str, has_following: bool) -> bool:
    return (
        has_following
        and len(line) <= MAX_HEADING_CHARS
        and len(line.split()) <= MAX_HEADING_WORDS
        and not line.endswith((".", ",", ";", ":", "!", "?", "।"))
        and not LIST_PREFIX.match(line)
        and not line[0].isdigit()
    )


def parse(data: bytes) -> ParsedDocument:
    text = _decode(data).replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [p.strip("\n") for p in PARAGRAPH_BREAK.split(text) if p.strip()]

    sections = SectionStack()
    blocks: list[ParsedBlock] = []

    def add(body: str, block_type: str) -> None:
        blocks.append(
            ParsedBlock(
                page_no=1,
                section_path=sections.path,
                order_idx=len(blocks),
                block_type=block_type,
                text=body,
            )
        )

    for index, paragraph in enumerate(paragraphs):
        lines = [normalize_text(ln) for ln in paragraph.split("\n") if ln.strip()]
        if not lines:
            continue

        # Markdown headings may sit directly above their paragraph.
        while lines and (m := MD_HEADING.match(lines[0])):
            title = normalize_text(m.group(2))
            sections.push(title, len(m.group(1)))
            add(title, "heading")
            lines = lines[1:]
        if not lines:
            continue

        has_following = index + 1 < len(paragraphs)
        if len(lines) == 1 and _looks_like_heading(lines[0], has_following):
            sections.push(lines[0], 1)
            add(lines[0], "heading")
            continue

        if all(LIST_PREFIX.match(ln) for ln in lines):
            for ln in lines:
                add(ln, "list_item")
            continue

        body = " ".join(lines)
        add(body, classify(body, is_heading=False))

    return ParsedDocument(blocks=blocks, page_count=1)
