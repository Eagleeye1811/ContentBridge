"""Format dispatch. Everything downstream consumes ParsedDocument only.

Documents, pasted text and images all become the same blocks here, so the
rest of the pipeline (indexing, the Fact Sheet, generation, verification)
never knows which kind of source it started from.
"""

from __future__ import annotations

from pathlib import Path

from app.services.ingestion import docx as docx_parser
from app.services.ingestion import image as image_parser
from app.services.ingestion import pdf as pdf_parser
from app.services.ingestion import pptx as pptx_parser
from app.services.ingestion import text as text_parser
from app.services.ingestion.base import ParsedBlock, ParsedDocument

SUPPORTED: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Text: pasted text arrives as a .txt upload and takes the same path.
    ".txt": "text/plain",
    ".md": "text/markdown",
    # Images are read by OCR; every paragraph keeps its box on the image.
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

_PARSERS = {
    ".pdf": pdf_parser.parse,
    ".docx": docx_parser.parse,
    ".pptx": pptx_parser.parse,
    ".txt": text_parser.parse,
    ".md": text_parser.parse,
    **{ext: (lambda data, ext=ext: image_parser.parse(data, ext)) for ext in IMAGE_EXTENSIONS},
}


class UnsupportedFormat(ValueError):
    pass


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def mime_for(filename: str) -> str:
    ext = extension_of(filename)
    if ext not in SUPPORTED:
        raise UnsupportedFormat(f"Unsupported file type '{ext}'. Allowed: {', '.join(SUPPORTED)}")
    return SUPPORTED[ext]


def parse_document(filename: str, data: bytes) -> ParsedDocument:
    ext = extension_of(filename)
    parser = _PARSERS.get(ext)
    if parser is None:
        raise UnsupportedFormat(f"Unsupported file type '{ext}'. Allowed: {', '.join(SUPPORTED)}")
    return parser(data)


__all__ = [
    "IMAGE_EXTENSIONS",
    "SUPPORTED",
    "ParsedBlock",
    "ParsedDocument",
    "UnsupportedFormat",
    "extension_of",
    "mime_for",
    "parse_document",
    "pdf_parser",
]
