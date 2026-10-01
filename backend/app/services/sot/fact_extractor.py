"""Fact extraction: the Source of Truth is born here.

Two rules make the rest of the system trustworthy:

1. Every fact must cite block ids that appear in the excerpt it was extracted
   from. Facts citing anything else are dropped, not repaired -- this is the
   guard against hallucinated citations.
2. Values are canonicalized on the way in, so downstream comparison is exact.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.services.indexing.chunker import BlockLike, estimate_tokens
from app.services.llm import get_llm
from app.services.sot.normalizer import canonicalize, slugify_key

log = logging.getLogger(__name__)

# Large excerpts keep the number of model calls low (free tiers allow only a
# few requests a day); the prompt asks for full coverage of each excerpt.
MAX_BATCH_TOKENS = 3000
MAX_QUOTE_CHARS = 600

FactType = Literal["metric", "date", "entity", "finding", "recommendation", "risk"]

SYSTEM = """You extract the key facts from a document so other content can be written
from them. The document may be an official notice, a report, a research paper,
a presentation or teaching material.

Hard rules:
- Extract ONLY what the excerpt states. Never infer, estimate or round.
- Every fact MUST cite one or more block ids that appear in the excerpt, using
  the exact bracketed labels shown (for example b3). A fact you cannot cite is
  a fact you must not report.
- Copy numbers exactly as written. Do not convert units or reformat figures.
- `statement` must be a single self-contained sentence a reader could verify
  against the cited block, understandable without the rest of the document.

Coverage:
- Capture every substantive point, not only numbers: figures, dates, names,
  definitions, explanations, findings, steps, examples, comparisons,
  recommendations and risks. Use `finding` for definitions, explanations and
  key points; `recommendation` for advice and steps.
- Report every substantive point in the excerpt; a long or dense excerpt may
  yield 20 or more facts. Report few only when it is mostly headers or
  boilerplate.
- Do not repeat the same fact twice. Skip page numbers, slide counters, running
  headers and decorative text.
"""


class ExtractedFact(BaseModel):
    key: str = Field(description="short snake_case identifier, e.g. credentials_compromised")
    type: FactType
    statement: str = Field(description="one self-contained verifiable sentence")
    value: str | None = Field(default=None, description="the bare figure or date, as written")
    unit: str | None = Field(default=None, description="percent, currency, days, or null")
    evidence_block_ids: list[str] = Field(description="bracketed block labels, e.g. ['b3']")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]


@dataclass(slots=True)
class Evidence:
    block_id: uuid.UUID
    quote: str
    char_start: int | None = None
    char_end: int | None = None


@dataclass(slots=True)
class ResolvedFact:
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)


def _batch_blocks(blocks: Sequence[BlockLike]) -> list[list[BlockLike]]:
    """Group blocks into prompt-sized excerpts, preferring section boundaries."""
    batches: list[list[BlockLike]] = []
    current: list[BlockLike] = []
    budget = 0

    for block in sorted(blocks, key=lambda b: b.order_idx):
        if not block.text.strip():
            continue
        tokens = estimate_tokens(block.text)
        if current and budget + tokens > MAX_BATCH_TOKENS:
            batches.append(current)
            current, budget = [], 0
        current.append(block)
        budget += tokens

    if current:
        batches.append(current)
    return batches


def _render_excerpt(batch: Sequence[BlockLike]) -> tuple[str, dict[str, BlockLike]]:
    """Label blocks b0..bN.

    Short labels keep the prompt small and, more importantly, make an invented
    citation obvious -- a model cannot accidentally guess a valid UUID.
    """
    id_map: dict[str, BlockLike] = {}
    lines: list[str] = []
    for i, block in enumerate(batch):
        label = f"b{i}"
        id_map[label] = block
        section = block.section_path or "(no section)"
        lines.append(f'[{label}] (page {block.page_no}, section "{section}")\n{block.text}')
    return "\n\n".join(lines), id_map


def _locate(statement: str, block_text: str) -> tuple[str, int | None, int | None]:
    """Find the statement inside the block so the UI can show an exact quote."""
    idx = block_text.find(statement)
    if idx >= 0:
        return statement, idx, idx + len(statement)

    # Fall back to the sentence with the most word overlap.
    words = {w.lower().strip(".,;:") for w in statement.split() if len(w) > 3}
    best, best_score = None, 0.0
    for sentence in block_text.replace("\n", " ").split(". "):
        if not sentence.strip():
            continue
        tokens = {w.lower().strip(".,;:") for w in sentence.split() if len(w) > 3}
        if not tokens:
            continue
        score = len(words & tokens) / len(words or tokens)
        if score > best_score:
            best, best_score = sentence.strip(), score

    if best and best_score >= 0.4:
        idx = block_text.find(best)
        return best, (idx if idx >= 0 else None), (idx + len(best) if idx >= 0 else None)

    return block_text[:MAX_QUOTE_CHARS], None, None


def _resolve(raw: ExtractedFact, id_map: dict[str, BlockLike]) -> ResolvedFact | None:
    """Validate citations and canonicalize. Returns None if the fact is unusable."""
    evidence: list[Evidence] = []
    for label in raw.evidence_block_ids:
        block = id_map.get(label.strip())
        if block is None:
            log.warning("dropping citation to unknown block %r for fact %r", label, raw.key)
            continue
        quote, start, end = _locate(raw.statement, block.text)
        evidence.append(
            Evidence(
                block_id=block.id, quote=quote[:MAX_QUOTE_CHARS], char_start=start, char_end=end
            )
        )

    if not evidence:
        log.warning("dropping uncited fact %r", raw.key)
        return None
    if not raw.statement.strip():
        return None

    canonical_value, unit = canonicalize(raw.value, raw.statement, raw.type)
    return ResolvedFact(
        key=slugify_key(raw.key or raw.statement),
        type=raw.type,
        statement=raw.statement.strip(),
        canonical_value=canonical_value,
        unit=raw.unit or unit,
        confidence=raw.confidence,
        evidence=evidence,
    )


def _dedupe(facts: list[ResolvedFact]) -> list[ResolvedFact]:
    """Keep one fact per (key, canonical_value), merging their evidence."""
    merged: dict[tuple[str, str | None], ResolvedFact] = {}
    for fact in facts:
        signature = (fact.key, fact.canonical_value)
        existing = merged.get(signature)
        if existing is None:
            merged[signature] = fact
            continue
        seen = {e.block_id for e in existing.evidence}
        existing.evidence.extend(e for e in fact.evidence if e.block_id not in seen)
        existing.confidence = max(existing.confidence, fact.confidence)
    return list(merged.values())


async def extract_facts(
    blocks: Sequence[BlockLike],
    *,
    on_progress: Callable[[float], None] | None = None,
) -> list[ResolvedFact]:
    llm = get_llm()
    batches = _batch_blocks(blocks)
    resolved: list[ResolvedFact] = []

    for i, batch in enumerate(batches):
        excerpt, id_map = _render_excerpt(batch)
        result = await llm.complete_structured(
            system=SYSTEM,
            prompt=f"Extract the Source of Truth from this excerpt.\n\n{excerpt}",
            schema=ExtractionResult,
        )
        for raw in result.facts:
            fact = _resolve(raw, id_map)
            if fact is not None:
                resolved.append(fact)
        if on_progress is not None:
            on_progress((i + 1) / len(batches))

    return _dedupe(resolved)
