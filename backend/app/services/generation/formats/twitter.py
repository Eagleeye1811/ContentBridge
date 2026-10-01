from app.services.generation.formats.base import FormatChoice, FormatOption, FormatSpec

SPEC = FormatSpec(
    key="twitter",
    name="Twitter/X Post",
    description="A short public post for X (Twitter), or a brief thread.",
    allowed_kinds=("post",),
    prompt_fragment="""Produce posts for X (Twitter). Each `post` node is ONE post; its `items`
are the lines of that post. Every post must be at most 270 characters in total.

- the first post states the single most important fact on its own
- plain, direct language; no jargon or acronyms the public will not know
- state only what the facts state; never speculate, reassure or exaggerate
- no emoji; hashtags only from terms that appear in the facts""",
    renderers=("text", "markdown"),
    max_nodes=1,
    max_node_chars=280,
    options=(
        FormatOption(
            key="format",
            label="Format",
            default="single",
            choices=(
                FormatChoice("single", "Single post", "Produce exactly one `post` node.", 1),
                FormatChoice(
                    "thread",
                    "Thread",
                    "Produce a thread of 3 to 5 `post` nodes that read in order.",
                    5,
                ),
            ),
        ),
        FormatOption(
            key="hashtags",
            label="Hashtags",
            default="yes",
            choices=(
                FormatChoice("yes", "Yes", "End the last post with 1 to 2 hashtags."),
                FormatChoice("no", "No", "Do not use hashtags."),
            ),
        ),
    ),
    defaults={
        "audience": "public",
        "tone": "neutral",
        "detail_level": "brief",
        "objective": "inform",
        "style": "plain_language",
    },
)
