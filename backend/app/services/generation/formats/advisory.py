from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="advisory",
    name="Advisory",
    description="An actionable security advisory for circulation.",
    allowed_kinds=("heading", "paragraph", "bullets", "callout"),
    prompt_fragment="""Produce an ADVISORY with this structure:
- one `callout` node carrying the overall severity and a one-line situation summary
- a `heading` "Background" followed by 1-2 `paragraph` nodes on what happened
- a `heading` "Impact" followed by a `paragraph` or `bullets` quantifying the effect
- a `heading` "Required Action" followed by one `bullets` node of 3-6 concrete,
  imperative actions
- a closing `paragraph` stating who to contact or report to, only if the facts
  support one

Be direct and specific. Every number must come from a fact you cite.""",
    renderers=("docx", "markdown", "html", "text"),
    max_nodes=14,
)
