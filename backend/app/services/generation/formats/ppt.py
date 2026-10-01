from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="ppt",
    name="Presentation",
    description="A slide deck for a meeting or briefing.",
    allowed_kinds=("slide",),
    prompt_fragment="""Produce a PRESENTATION as `slide` nodes only:
- every slide has a short `title` (under 8 words) and 3 to 5 bullets in
  `items`. A slide without bullets is invalid.
- order: an overview slide first, then the main points, then a closing slide
  with the key takeaways or actions the facts support
- each bullet is a fragment, not a sentence: under 12 words, no trailing full
  stop, and states something specific from the facts
- `notes` holds what the speaker says, 1 to 3 sentences; never put the slide's
  only content there

Use as many slides as the facts genuinely support, up to the number asked for.
Never pad a slide with generic filler such as "management must review this" or
"this is important"; fewer, fuller slides are better.""",
    renderers=("pptx", "markdown", "html"),
    max_nodes=10,
    options=(
        FormatOption(
            key="slides",
            label="Slides",
            default="8",
            choices=(
                FormatChoice("5", "5", "Produce up to 5 slides.", max_nodes=5),
                FormatChoice("8", "8", "Produce up to 8 slides.", max_nodes=8),
                FormatChoice("12", "12", "Produce up to 12 slides.", max_nodes=12),
            ),
        ),
        FormatOption(
            key="presenting_to",
            label="Presenting to",
            default="officials",
            choices=(
                FormatChoice("team", "Team", audience="technical"),
                FormatChoice("officials", "Senior officials", audience="management"),
                FormatChoice("public", "Public", audience="public"),
            ),
        ),
    ),
    defaults={"tone": "formal", "objective": "inform", "style": "structured"},
)
