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

from pydantic import BaseModel, ConfigDict, Field, field_validator

NodeKind = Literal[
    "heading",
    "paragraph",
    "bullets",
    "slide",
    "table",
    "callout",
    "quote",
    "post",
    # Infographic section: title, data points in items, visual direction in notes.
    "panel",
    # Video storyboard scene: narration in text, overlays in items, visuals in notes.
    "scene",
]

Severity = Literal["info", "low", "medium", "high", "critical"]


class Node(BaseModel):
    id: str = Field(description="short stable id unique within the document, e.g. n3")
    kind: NodeKind
    text: str | None = Field(
        default=None,
        description="body text for paragraph/heading/quote, caption for a panel, "
        "narration for a scene",
    )
    items: list[str] | None = Field(
        default=None,
        description="lines for bullets/slide/post, data points for a panel, "
        "on-screen text for a scene",
    )
    level: int | None = Field(default=None, description="heading depth, 1-3")
    title: str | None = Field(default=None, description="slide, callout, panel or scene title")
    notes: str | None = Field(
        default=None,
        description="speaker notes for a slide; visual recommendation for a panel or scene",
    )
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


def _require_lists(schema: dict) -> None:
    schema["required"] = sorted({*schema.get("required", []), "items", "rows"})


class DraftNode(Node):
    """What the model is asked to fill in.

    Identical to `Node` except that `items` and `rows` are always lists and are
    marked required in the schema. Gemini leaves out optional fields, so a
    slide's bullets were never written; required, it must fill them in (an
    empty list where unused). Validation still accepts them missing.
    """

    model_config = ConfigDict(json_schema_extra=_require_lists)

    items: list[str] = Field(  # type: ignore[assignment]
        default_factory=list,
        description="lines for bullets/slide/post, data points for a panel, "
        "on-screen text for a scene; empty list if unused",
    )
    rows: list[list[str]] = Field(  # type: ignore[assignment]
        default_factory=list, description="table rows, first row is header; empty if unused"
    )

    @field_validator("items", "rows", mode="before")
    @classmethod
    def _none_is_empty(cls, value: object) -> object:
        return [] if value is None else value


class DraftIR(BaseModel):
    title: str
    nodes: list[DraftNode]

    def to_content_ir(self) -> ContentIR:
        """Back to the stored shape: unused lists become None again."""
        return ContentIR(
            title=self.title,
            nodes=[
                Node(
                    **{
                        **n.model_dump(),
                        "items": n.items or None,
                        "rows": n.rows or None,
                    }
                )
                for n in self.nodes
            ],
        )


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
