from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="ppt",
    name="Presentation",
    description="A slide deck for a meeting or briefing.",
    allowed_kinds=("slide",),
    prompt_fragment="""Produce a PRESENTATION deck as `slide` nodes only:
- Every slide must communicate one clear takeaway, have a descriptive title, and contain structured items or table rows.
- Build a complete, useful narrative based strictly on source facts:
  * Overview/Executive summary: core message, scope, key status, main takeaway statement.
  * Technical/Contextual details: architecture, scope, methodology, timeline, or key findings using appropriate layouts (layout='two_column', 'timeline', or 'process').
  * Findings/Data & Analysis: prominent actual figures, metrics, and comparisons (layout='metrics', 'comparison', or 'table'). Use descriptive labels, NEVER generic placeholders like '#1' or 'Event 1'.
  * Impact/Trade-offs: observed impact vs potential implications, resource or risk considerations.
  * Action Plan/Recommendations: practical steps, milestones, or priorities grouped logically.
  * Conclusion/Key Takeaways: synthesis of main findings, next steps, and decision requirements (layout='key_takeaways').

- Detail Level Guidelines:
  * Concise: 2-3 brief, high-impact points per slide; focus strictly on core message and essential facts.
  * Balanced: 3-4 structured points per slide with explanation of significance and supporting context.
  * Detailed: 4-6 comprehensive points per slide with fuller explanations, context, specific metrics, relationships, and unresolved questions.

- Do not copy raw unstructured paragraphs. Rephrase facts into clear presentation bullet points.
- Do not invent statistics, figures, budgets, or facts not present in the source.
- Preserve factual qualifications, assumptions, and remaining uncertainties.""",
    renderers=("pptx", "pdf", "markdown", "html"),
    max_nodes=10,
    options=(
        FormatOption(
            key="slides",
            label="Slides",
            default="auto",
            choices=(
                FormatChoice("5", "5 slides", "Produce up to 5 slides.", max_nodes=5),
                FormatChoice("8", "8 slides", "Produce up to 8 slides.", max_nodes=8),
                FormatChoice("10", "10 slides", "Produce exactly 10 slides.", max_nodes=10),
                FormatChoice("12", "12 slides", "Produce up to 12 slides.", max_nodes=12),
                FormatChoice("15", "15 slides", "Produce up to 15 slides.", max_nodes=15),
                FormatChoice("20", "20 slides", "Produce up to 20 slides.", max_nodes=20),
                FormatChoice("auto", "Let AI decide", "Produce a reasonable number of slides (between 5 and 15) based on the facts.", max_nodes=25),
            ),
        ),
        FormatOption(
            key="presenting_to",
            label="Presenting to",
            default="officials",
            choices=(
                FormatChoice("team", "Team", audience="technical"),
                FormatChoice("officials", "Officials", audience="officer"),
                FormatChoice("public", "Public", audience="public"),
                FormatChoice("technical", "Technical Team", audience="technical"),
                FormatChoice("researchers", "Researchers / Experts", audience="technical"),
                FormatChoice("students", "Students / Trainees", audience="public"),
                FormatChoice("senior_leadership", "Senior Leadership", audience="management"),
            ),
        ),
    ),
    defaults={"tone": "formal", "objective": "inform", "style": "structured", "detail_level": "balanced"},
)
