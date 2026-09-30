from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="ppt",
    name="Presentation",
    description="A briefing deck for a meeting or review.",
    allowed_kinds=("slide",),
    prompt_fragment="""Produce a PRESENTATION as `slide` nodes only:
- 6 to 10 slides, each with a `title` and 3-5 short `items`
- open with a situation slide, then impact, then findings, then actions
- each bullet is a fragment, not a sentence: under 12 words, no trailing full stop
- put the spoken detail in `notes`, not on the slide

A slide is a prompt for a speaker, not a document. If a bullet needs a comma
and a subordinate clause, it belongs in the notes.""",
    renderers=("pptx", "markdown", "html"),
    max_nodes=10,
)
