from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="summary",
    name="Executive Summary",
    description="A short briefing for a decision maker.",
    allowed_kinds=("heading", "paragraph", "bullets"),
    prompt_fragment="""Produce an EXECUTIVE SUMMARY:
- a `heading` with the subject
- 3-5 `paragraph` nodes, each a tight paragraph of 2-4 sentences
- optionally one closing `bullets` node of key figures, at most 5 lines

Lead with what a decision maker needs first: what happened, how big it is, what
is being asked of them. No preamble, no restating the document structure.""",
    renderers=("markdown", "text"),
    max_nodes=10,
)
