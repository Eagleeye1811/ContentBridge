"""Renderer registry.

Every renderer is a pure function of ContentIR: same input, same bytes, no LLM
call. That is what makes export reproducible and independently testable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.schemas.content_ir import ContentIR
from app.services.rendering import docx_writer, html_writer, markdown, pdf_writer, pptx_writer, srt, text


@dataclass(frozen=True, slots=True)
class RendererSpec:
    key: str
    name: str
    extension: str
    media_type: str
    binary: bool
    fn: Callable[..., str | bytes]


RENDERERS: dict[str, RendererSpec] = {
    spec.key: spec
    for spec in (
        RendererSpec("markdown", "Markdown", "md", "text/markdown", False, markdown.render),
        RendererSpec("text", "Plain text", "txt", "text/plain", False, text.render),
        RendererSpec("html", "HTML", "html", "text/html", False, html_writer.render),
        RendererSpec("srt", "Subtitles", "srt", "application/x-subrip", False, srt.render),
        RendererSpec(
            "docx",
            "Word",
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            True,
            docx_writer.render,
        ),
        RendererSpec(
            "pptx",
            "PowerPoint",
            "pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            True,
            pptx_writer.render,
        ),
        RendererSpec(
            "pdf",
            "PDF Document",
            "pdf",
            "application/pdf",
            True,
            pdf_writer.render,
        ),
    )
}


class UnknownRenderer(ValueError):
    pass


def get_renderer(key: str) -> RendererSpec:
    spec = RENDERERS.get(key)
    if spec is None:
        raise UnknownRenderer(
            f"Unknown renderer {key!r}. Available: {', '.join(sorted(RENDERERS))}"
        )
    return spec


def render_bytes(ir: ContentIR, key: str, **kwargs: object) -> bytes:
    spec = get_renderer(key)
    result = spec.fn(ir, **kwargs)
    return result if isinstance(result, bytes) else result.encode("utf-8")


def render_text(ir: ContentIR, key: str, **kwargs: object) -> str:
    """Text renderers only. Raises for binary formats rather than returning mojibake."""
    spec = get_renderer(key)
    if spec.binary:
        raise UnknownRenderer(f"{spec.name} is a binary format; use render_bytes.")
    result = spec.fn(ir, **kwargs)
    assert isinstance(result, str)
    return result


# Kept for existing call sites that only deal in text.
render = render_text

EXTENSIONS = {k: s.extension for k, s in RENDERERS.items()}
MEDIA_TYPES = {k: s.media_type for k, s in RENDERERS.items()}
