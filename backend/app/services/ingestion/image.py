"""Image -> blocks via OCR (Tesseract).

Each OCR paragraph becomes a block with a bounding box in image pixels, so an
image source gets the same click-to-highlight traceability as a PDF: the viewer
draws boxes as fractions of `page_width`/`page_height`, whatever the units.

Headings are inferred the way the PDF parser infers them, from size: a short
paragraph whose lines are markedly taller than the image's typical line.

Tesseract runs as a subprocess, so the only requirement is the `tesseract`
binary (plus `hin`/`mar` language data for Devanagari, used when installed).
"""

from __future__ import annotations

import csv
import io
import shutil
import statistics
import subprocess
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.services.ingestion.base import (
    ParsedBlock,
    ParsedDocument,
    SectionStack,
    classify,
    normalize_text,
)

PREFERRED_LANGUAGES = ("eng", "hin", "mar")
MIN_WORD_CONFIDENCE = 30.0
HEADING_HEIGHT_RATIO = 1.35
MAX_HEADING_WORDS = 12
OCR_TIMEOUT_SECONDS = 120


class OCRUnavailable(RuntimeError):
    pass


@dataclass(slots=True)
class _Paragraph:
    words: list[str] = field(default_factory=list)
    line_heights: list[int] = field(default_factory=list)
    x0: int = 10**9
    y0: int = 10**9
    x1: int = 0
    y1: int = 0

    def add_word(self, text: str, left: int, top: int, width: int, height: int) -> None:
        self.words.append(text)
        self.x0 = min(self.x0, left)
        self.y0 = min(self.y0, top)
        self.x1 = max(self.x1, left + width)
        self.y1 = max(self.y1, top + height)


def _binary() -> str:
    path = shutil.which("tesseract")
    if path is None:
        raise OCRUnavailable(
            "Image sources need the Tesseract OCR engine. Install it "
            "(brew install tesseract / apt-get install tesseract-ocr) and retry."
        )
    return path


@lru_cache(maxsize=1)
def _languages() -> str:
    try:
        listed = subprocess.run(
            [_binary(), "--list-langs"], capture_output=True, text=True, timeout=30, check=True
        ).stdout.split()
    except (subprocess.SubprocessError, OSError):
        return "eng"
    chosen = [lang for lang in PREFERRED_LANGUAGES if lang in listed]
    return "+".join(chosen) or "eng"


def _run_tesseract(data: bytes, suffix: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / f"source{suffix}"
        source.write_bytes(data)
        try:
            result = subprocess.run(
                [_binary(), str(source), "stdout", "-l", _languages(), "tsv"],
                capture_output=True,
                text=True,
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("OCR timed out on this image") from exc
    if result.returncode != 0:
        raise RuntimeError(f"OCR failed: {result.stderr.strip()[:300]}")
    return result.stdout


def parse_tsv(tsv: str) -> ParsedDocument:
    """Turn Tesseract TSV into blocks. Split out so it is testable without OCR."""
    page_w = page_h = 0
    paragraphs: dict[tuple[int, int, int], _Paragraph] = {}

    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        try:
            level = int(row["level"])
            left, top = int(row["left"]), int(row["top"])
            width, height = int(row["width"]), int(row["height"])
        except (KeyError, TypeError, ValueError):
            continue
        key = (int(row["page_num"]), int(row["block_num"]), int(row["par_num"]))

        if level == 1:
            page_w, page_h = max(page_w, width), max(page_h, height)
        elif level == 4:
            paragraphs.setdefault(key, _Paragraph()).line_heights.append(height)
        elif level == 5:
            text = (row.get("text") or "").strip()
            try:
                confidence = float(row.get("conf") or -1)
            except ValueError:
                confidence = -1
            if text and confidence >= MIN_WORD_CONFIDENCE:
                paragraphs.setdefault(key, _Paragraph()).add_word(text, left, top, width, height)

    kept = [p for p in paragraphs.values() if p.words]
    if not kept:
        return ParsedDocument(blocks=[], page_count=1)

    # Typical line height, weighted by word count so body text dominates even
    # when an image holds only a heading and a paragraph or two.
    weighted = [
        statistics.mean(p.line_heights) for p in kept if p.line_heights for _ in p.words
    ] or [1]
    typical = statistics.median(weighted)

    sections = SectionStack()
    blocks: list[ParsedBlock] = []
    # Reading order: top to bottom, then left to right.
    for para in sorted(kept, key=lambda p: (p.y0, p.x0)):
        text = normalize_text(" ".join(para.words))
        if not text:
            continue
        mean_height = statistics.mean(para.line_heights) if para.line_heights else typical
        is_heading = (
            mean_height >= typical * HEADING_HEIGHT_RATIO and len(text.split()) <= MAX_HEADING_WORDS
        )
        if is_heading:
            sections.push(text, 1)
        blocks.append(
            ParsedBlock(
                page_no=1,
                section_path=sections.path,
                order_idx=len(blocks),
                block_type=classify(text, is_heading),
                text=text,
                bbox={
                    "x0": para.x0,
                    "y0": para.y0,
                    "x1": para.x1,
                    "y1": para.y1,
                    "page_width": page_w or para.x1,
                    "page_height": page_h or para.y1,
                },
            )
        )
    return ParsedDocument(blocks=blocks, page_count=1)


def parse(data: bytes, suffix: str = ".png") -> ParsedDocument:
    parsed = parse_tsv(_run_tesseract(data, suffix))
    if not parsed.blocks:
        raise RuntimeError(
            "No readable text was found in this image. Use a sharper, higher-resolution "
            "image of the document."
        )
    return parsed
