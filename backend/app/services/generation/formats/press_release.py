from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="press_release",
    name="Press Release",
    description="A public statement for newspapers and media.",
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
    options=(
        FormatOption(
            key="length",
            label="Length",
            default="standard",
            choices=(
                FormatChoice("short", "Short", "Keep the body to 2 paragraphs.", max_nodes=5),
                FormatChoice("standard", "Standard"),
            ),
        ),
        FormatOption(
            key="quote",
            label="Quote",
            help="Only when the source has a real statement from someone.",
            default="if_available",
            choices=(
                FormatChoice("if_available", "If available"),
                FormatChoice("none", "No quote", "Do not produce a `quote` node."),
            ),
        ),
    ),
    defaults={
        "audience": "public",
        "tone": "neutral",
        "objective": "inform",
        "style": "narrative",
    },
)
