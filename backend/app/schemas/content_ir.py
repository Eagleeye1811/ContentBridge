"""ContentIR: the format-neutral representation every output shares.

The LLM never emits PPTX, DOCX or Markdown. It emits this. Renderers are then
pure functions of ContentIR, which is what makes export reproducible, editing
uniform and verification format-agnostic.

Design note: `Node` is one flat model with optional fields rather than a
discriminated union. Union support in provider structured-output schemas is
inconsistent, and a flat node survives every provider intact. `FormatSpec`
constrains which `kind` values are allowed for a given output type.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NodeKind = Literal[
    "heading",
    "paragraph",
    "bullets",
    "slide",
    "table",
    "callout",
    "quote",
    "post",
]

Severity = Literal["info", "low", "medium", "high", "critical"]


class Node(BaseModel):
    id: str = Field(description="short stable id unique within the document, e.g. n3")
    kind: NodeKind
    text: str | None = Field(default=None, description="body text for paragraph/heading/quote")
    items: list[str] | None = Field(default=None, description="lines for bullets/slide/post")
    level: int | None = Field(default=None, description="heading depth, 1-3")
    title: str | None = Field(default=None, description="slide or callout title")
    notes: str | None = Field(default=None, description="speaker notes for a slide")
    rows: list[list[str]] | None = Field(
        default=None, description="table rows, first row is header"
    )
    severity: Severity | None = None
    fact_ids: list[str] = Field(
        default_factory=list,
        description="labels of the facts this node is built from, e.g. ['f2','f7']",
    )


class ContentIR(BaseModel):
    title: str
    nodes: list[Node]


def iter_text(node: Node) -> list[str]:
    """Every human-readable string in a node, for verification and rendering."""
    out: list[str] = []
    for value in (node.title, node.text, node.notes):
        if value:
            out.append(value)
    if node.items:
        out.extend(i for i in node.items if i)
    if node.rows:
        out.extend(cell for row in node.rows for cell in row if cell)
    return out


def node_word_count(ir: ContentIR) -> int:
    return sum(len(t.split()) for node in ir.nodes for t in iter_text(node))
