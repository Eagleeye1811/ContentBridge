from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="report",
    name="Report",
    description="A structured report for the record.",
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
)
