"""The one shape every parser produces.

PDF, DOCX and PPTX differ wildly, but downstream code only ever sees
`ParsedBlock`. A block knows where it came from — that is the whole point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# "1. ", "1) ", "- ", "* ", "• "
LIST_PREFIX = re.compile(r"^\s*(?:[•‣●▪\-\*·]|\(?\d+[.)]|[a-z][.)])\s+")


@dataclass(slots=True)
class ParsedBlock:
    page_no: int
    section_path: str
    order_idx: int
    block_type: str
    text: str
    # {"x0","y0","x1","y1","page_width","page_height"} in PDF points, or None
    # for formats with no geometry. Stored as fractions of the page by the UI.
    bbox: dict | None = None


@dataclass(slots=True)
class ParsedDocument:
    blocks: list[ParsedBlock] = field(default_factory=list)
    page_count: int = 0


class SectionStack:
    """Tracks the current heading path, e.g. `Findings > Credential Exposure`."""

    def __init__(self) -> None:
        self._stack: list[str] = []

    def push(self, title: str, level: int) -> None:
        level = max(1, level)
        del self._stack[level - 1 :]
        self._stack.append(title.strip())

    @property
    def path(self) -> str:
        return " > ".join(self._stack)


def classify(text: str, is_heading: bool) -> str:
    if is_heading:
        return "heading"
    if LIST_PREFIX.match(text):
        return "list_item"
    return "paragraph"


def normalize_text(raw: str) -> str:
    """Collapse the intra-line whitespace PDF extraction tends to produce."""
    return re.sub(r"[ \t ]+", " ", raw.replace("­", "")).strip()
