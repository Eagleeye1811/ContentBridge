from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="email",
    name="Official Email",
    description="A circulation email with a clear ask.",
    allowed_kinds=("heading", "paragraph", "bullets"),
    prompt_fragment="""Produce an OFFICIAL EMAIL. The document `title` is the subject line:
specific and under 80 characters, with no "Re:" or "FWD:".

Structure:
- a `paragraph` salutation addressed to the audience
- 2-3 `paragraph` nodes: what happened, what it means for the reader
- one `bullets` node of what the reader must do, if the facts support actions
- a closing `paragraph` with the sign-off

Write as a person to a person. No headings, no bold labels, no bullet lists
of background.""",
    renderers=("text", "html", "markdown"),
    max_nodes=8,
)
