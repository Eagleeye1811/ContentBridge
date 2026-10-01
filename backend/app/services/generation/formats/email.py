from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="email",
    name="Official Email",
    description="A ready-to-send email with a clear request.",
    allowed_kinds=("heading", "paragraph", "bullets"),
    prompt_fragment="""Produce an OFFICIAL EMAIL. The document `title` is the subject line:
specific and under 80 characters, with no "Re:" or "FWD:".

Structure:
- a short greeting `paragraph` (at most 6 words; it needs no fact citation):
  "Dear colleagues," for staff, "Dear Sir/Madam," for senior officials,
  "Dear residents," for citizens
- 2-3 `paragraph` nodes: what happened, what it means for the reader
- one `bullets` node of what the reader must do, if the facts support actions
- a short sign-off `paragraph`, e.g. "Regards," followed by the issuing body
  if the facts name one (at most 12 words; it needs no fact citation)

Write as a person to a person. No headings, no bold labels, no bullet lists
of background.""",
    renderers=("text", "html", "markdown"),
    max_nodes=8,
    uncited_max_words=12,
    options=(
        FormatOption(
            key="sending_to",
            label="Sending to",
            default="staff",
            choices=(
                FormatChoice("staff", "Staff", audience="officer"),
                FormatChoice("officials", "Senior officials", audience="management"),
                FormatChoice("citizens", "Citizens", audience="public"),
            ),
        ),
        FormatOption(
            key="length",
            label="Length",
            default="short",
            choices=(
                FormatChoice("short", "Short", "Keep the body to 2 short paragraphs."),
                FormatChoice("standard", "Standard"),
            ),
        ),
    ),
    defaults={"tone": "formal", "objective": "instruct", "style": "structured"},
)
