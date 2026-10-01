from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="linkedin",
    name="LinkedIn Post",
    description="A professional post for your organisation's LinkedIn page.",
    allowed_kinds=("post",),
    prompt_fragment="""Produce exactly one `post` node: a LinkedIn post. Its `items` are the
paragraphs of the post, in order:

- a first line that states the single most important fact (this is what shows
  before "see more"), under 150 characters
- 2 to 4 short paragraphs of one or two sentences each, covering impact and
  what is being done, as the facts state them
- if the facts recommend an action, one paragraph stating it plainly
- optionally a final line of 2 to 4 hashtags built only from terms that appear
  in the facts (an organisation, a system, a topic named there)

Keep the whole post under 1,300 characters. Professional and measured: no
emoji, no clickbait, no rhetorical questions, and never speculate or reassure
beyond the facts.""",
    renderers=("text", "markdown"),
    max_nodes=1,
    options=(
        FormatOption(
            key="length",
            label="Length",
            default="short",
            choices=(
                FormatChoice(
                    "short", "Short", "Keep the whole post under 600 characters, 2-3 paragraphs."
                ),
                FormatChoice("standard", "Standard"),
            ),
        ),
        FormatOption(
            key="hashtags",
            label="Hashtags",
            default="yes",
            choices=(
                FormatChoice("yes", "Yes"),
                FormatChoice("no", "No", "Do not add a hashtag line."),
            ),
        ),
    ),
    defaults={
        "audience": "public",
        "tone": "conversational",
        "objective": "awareness",
        "style": "plain_language",
    },
)
