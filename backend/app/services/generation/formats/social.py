from app.services.generation.formats.base import FormatSpec

SPEC = FormatSpec(
    key="social",
    name="Social Media Post",
    description="A short public post.",
    allowed_kinds=("post",),
    prompt_fragment="""Produce 1 to 3 `post` nodes. Each node's `items` are the lines of one
post, and the whole post must stay under 280 characters.

- plain language, no jargon, no acronyms the public will not know
- state only what the facts state; never reassure or speculate beyond them
- no emoji, no hashtags unless a named entity in the facts warrants one
- if the facts do not support a public statement, produce a single post that
  says only what is confirmed""",
    renderers=("text", "markdown"),
    max_nodes=3,
)
