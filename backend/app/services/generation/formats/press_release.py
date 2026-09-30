from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="press_release",
    name="Press Release",
    description="A statement for the press.",
    allowed_kinds=("heading", "paragraph", "quote"),
    prompt_fragment="""Produce a PRESS RELEASE:
- a `heading` (level 1) as the release headline
- a `paragraph` dateline in the form "CITY, DATE -" followed by the lede,
  which must answer what happened and how large it is in one sentence
- 2-4 `paragraph` nodes of body, most important first
- optionally one `quote` node, but ONLY if the facts contain an attributable
  statement. Never invent a spokesperson or a quotation.
- a closing `paragraph` of boilerplate about the issuing body, only if the
  facts describe it

Neutral, factual register. No adjectives that the facts do not support.""",
    renderers=("docx", "markdown", "html"),
    max_nodes=10,
)
