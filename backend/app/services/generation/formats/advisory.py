from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="advisory",
    name="Advisory",
    description="An official notice telling readers what happened and what to do.",
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
    options=(
        FormatOption(
            key="issued_to",
            label="Issued to",
            default="officials",
            choices=(
                FormatChoice("officials", "Officials", audience="officer"),
                FormatChoice("public", "Public", audience="public"),
            ),
        ),
        FormatOption(
            key="length",
            label="Length",
            default="short",
            choices=(
                FormatChoice(
                    "short", "Short", "Keep it brief: at most 3 required actions.", max_nodes=8
                ),
                FormatChoice("detailed", "Detailed"),
            ),
        ),
    ),
    defaults={"tone": "formal", "objective": "instruct", "style": "structured"},
)
