from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="infographic",
    name="Infographic",
    description="Text, key numbers and design ideas for a one-page infographic.",
    allowed_kinds=("heading", "panel", "callout"),
    prompt_fragment="""Produce an INFOGRAPHIC PACKAGE: the content and design brief a designer
needs to lay out one infographic. Do not describe the whole image in prose.

- one level-1 `heading`: the infographic headline, under 10 words
- 4 to 7 `panel` nodes, one per visual section, in reading order. For each:
  - `title`: the panel label, under 6 words
  - `items`: 1 to 3 data points to print on the panel, each led by its figure
    or date exactly as the fact states it, under 12 words each
  - `text`: optional one-sentence caption
  - `notes`: the visual recommendation for that panel only -- chart or icon
    type (for example "single big number", "bar chart", "timeline", "icon
    grid"), and what it should show. Never introduce a figure in `notes` that
    is not in `items`.
- optionally one `callout` with the key takeaway or required action, with a
  `severity` where the facts support one

Put the most important figure in the first panel.""",
    renderers=("html", "markdown", "docx"),
    max_nodes=9,
    options=(
        FormatOption(
            key="sections",
            label="Sections",
            default="6",
            choices=(
                FormatChoice("4", "4", "Produce exactly 4 `panel` nodes.", max_nodes=6),
                FormatChoice("6", "6", "Produce 5 to 6 `panel` nodes.", max_nodes=8),
                FormatChoice("8", "8", "Produce 8 `panel` nodes.", max_nodes=10),
            ),
        ),
        FormatOption(
            key="shape",
            label="Shape",
            default="poster",
            choices=(
                FormatChoice(
                    "poster", "Poster", "Design for a tall, vertical poster read top to bottom."
                ),
                FormatChoice(
                    "square",
                    "Square",
                    "Design for a square social-media image; keep text minimal.",
                ),
                FormatChoice("wide", "Wide", "Design for a wide 16:9 layout read left to right."),
            ),
        ),
    ),
    defaults={
        "audience": "public",
        "tone": "neutral",
        "detail_level": "brief",
        "objective": "awareness",
        "style": "data_driven",
    },
)
