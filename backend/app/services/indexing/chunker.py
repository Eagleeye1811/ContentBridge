"""Chunking that preserves provenance.

A chunk never spans a section boundary and always records the blocks it was
built from, so a retrieval hit can be resolved back to pages and quotes.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

# Rough tokens-per-character for English. Good enough for budgeting; we are
# sizing chunks, not billing for them.
CHARS_PER_TOKEN = 4
DEFAULT_MAX_TOKENS = 450
DEFAULT_OVERLAP_BLOCKS = 1


class BlockLike(Protocol):
    id: uuid.UUID
    page_no: int
    section_path: str
    order_idx: int
    text: str


@dataclass(slots=True)
class TextChunk:
    text: str
    block_ids: list[uuid.UUID] = field(default_factory=list)
    page_no: int = 1
    section_path: str = ""
    token_count: int = 0


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _flush(buffer: Sequence[BlockLike]) -> TextChunk:
    text = "\n".join(b.text for b in buffer)
    return TextChunk(
        text=text,
        block_ids=[b.id for b in buffer],
        # A chunk is anchored to where it starts.
        page_no=buffer[0].page_no,
        section_path=buffer[0].section_path,
        token_count=estimate_tokens(text),
    )


def chunk_blocks(
    blocks: Iterable[BlockLike],
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_blocks: int = DEFAULT_OVERLAP_BLOCKS,
) -> list[TextChunk]:
    """Group consecutive blocks into retrieval units.

    Blocks are only grouped while they share a section path; a section change
    always starts a new chunk, which keeps retrieved context coherent and makes
    the section attribution on a hit honest.
    """
    chunks: list[TextChunk] = []
    buffer: list[BlockLike] = []
    budget = 0
    current_section: str | None = None

    for block in sorted(blocks, key=lambda b: b.order_idx):
        if not block.text.strip():
            continue
        tokens = estimate_tokens(block.text)

        section_changed = current_section is not None and block.section_path != current_section
        too_big = buffer and budget + tokens > max_tokens

        if section_changed or too_big:
            chunks.append(_flush(buffer))
            # Carry a little context forward, but never across a section.
            tail = [] if section_changed else buffer[-overlap_blocks:] if overlap_blocks else []
            buffer = list(tail)
            budget = sum(estimate_tokens(b.text) for b in buffer)

        buffer.append(block)
        budget += tokens
        current_section = block.section_path

    if buffer:
        chunks.append(_flush(buffer))
    return chunks
