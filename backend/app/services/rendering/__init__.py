"""Renderer registry. Format-specific code lives here and nowhere else."""

from __future__ import annotations

from collections.abc import Callable

from app.schemas.content_ir import ContentIR
from app.services.rendering import markdown, text

Renderer = Callable[..., str]

RENDERERS: dict[str, Renderer] = {
    "markdown": markdown.render,
    "text": text.render,
}

EXTENSIONS = {"markdown": "md", "text": "txt"}
MEDIA_TYPES = {"markdown": "text/markdown", "text": "text/plain"}


class UnknownRenderer(ValueError):
    pass


def render(ir: ContentIR, renderer: str, **kwargs: object) -> str:
    fn = RENDERERS.get(renderer)
    if fn is None:
        raise UnknownRenderer(
            f"Unknown renderer {renderer!r}. Available: {', '.join(sorted(RENDERERS))}"
        )
    return fn(ir, **kwargs)
