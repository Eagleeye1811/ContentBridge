from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="report",
    name="Report",
    description="A complete, structured report for the record.",
    allowed_kinds=("heading", "paragraph", "bullets", "table"),
    prompt_fragment="""Produce a REPORT with nested sections:
- a level-1 `heading` per major section, level-2 for subsections
- `paragraph` nodes for narrative, `bullets` for enumerable points
- at least one `table` node summarising the key figures, where the first row
  is the header (for example "Metric" and "Value")

Suggested sections, kept only where the facts support them: Summary, Scope,
Timeline, Findings, Impact, Recommendations, Conclusion.

This is the archival record. Prefer completeness over brevity, but never pad
a section the facts cannot fill.""",
    renderers=("docx", "markdown", "html"),
    max_nodes=40,
    options=(
        FormatOption(
            key="depth",
            label="Depth",
            default="full",
            choices=(
                FormatChoice(
                    "overview",
                    "Overview",
                    "Keep only Summary, Findings and Recommendations sections.",
                    max_nodes=16,
                ),
                FormatChoice("full", "Full report"),
            ),
        ),
        FormatOption(
            key="table",
            label="Table of figures",
            default="yes",
            choices=(
                FormatChoice("yes", "Yes"),
                FormatChoice("no", "No", "Do not produce a `table` node."),
            ),
        ),
    ),
    defaults={
        "audience": "officer",
        "tone": "formal",
        "detail_level": "comprehensive",
        "objective": "record",
        "style": "structured",
    },
)
