from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="summary",
    name="Executive Summary",
    description="A short overview for a busy decision maker.",
    allowed_kinds=("heading", "paragraph", "bullets"),
    prompt_fragment="""Produce an EXECUTIVE SUMMARY:
- a `heading` with the subject
- 3-5 `paragraph` nodes, each a tight paragraph of 2-4 sentences
- optionally one closing `bullets` node of key figures, at most 5 lines

Lead with what a decision maker needs first: what happened, how big it is, what
is being asked of them. No preamble, no restating the document structure.""",
    renderers=("docx", "markdown", "html"),
    max_nodes=10,
    options=(
        FormatOption(
            key="length",
            label="Length",
            default="half_page",
            choices=(
                FormatChoice(
                    "paragraph", "One paragraph", "Write a single `paragraph` of 3-5 sentences."
                ),
                FormatChoice("half_page", "Half page"),
                FormatChoice("full_page", "One page", "Write 5 to 7 paragraphs."),
            ),
        ),
        FormatOption(
            key="layout",
            label="Layout",
            default="paragraphs",
            choices=(
                FormatChoice("paragraphs", "Paragraphs"),
                FormatChoice(
                    "bullets",
                    "Bullet points",
                    "After the heading, use `bullets` nodes of short points instead of paragraphs.",
                ),
            ),
        ),
    ),
    defaults={
        "audience": "management",
        "tone": "formal",
        "detail_level": "brief",
        "objective": "inform",
        "style": "data_driven",
    },
)
