"""Splitting generated content into atomic, checkable claims."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.content_ir import ContentIR, Node

# Devanagari ends a sentence with a danda, not a full stop, so Hindi and
# Marathi output would otherwise arrive as one enormous unsplittable claim.
DANDA = "\u0964\u0965"

# Split on sentence punctuation followed by whitespace and a capital/digit,
# which leaves "e.g." and "No. 4" alone in the common cases.
SENTENCE = re.compile(rf"(?<=[.!?{DANDA}])\s+(?=[\"'(\[]?[A-Za-z\u0900-\u097F0-9])")
# A danda is frequently written without a following space.
DANDA_SPLIT = re.compile(rf"(?<=[{DANDA}])(?=[\u0900-\u097F])")
MIN_CLAIM_CHARS = 12


@dataclass(slots=True)
class Claim:
    node_id: str
    text: str
    fact_ids: list[str]


def _sentences(text: str) -> list[str]:
    parts: list[str] = []
    for chunk in SENTENCE.split(text.strip()):
        parts.extend(DANDA_SPLIT.split(chunk))
    return [p.strip() for p in parts if len(p.strip()) >= MIN_CLAIM_CHARS]


def _node_claims(node: Node) -> list[str]:
    match node.kind:
        case "heading":
            # Navigation, not a claim.
            return []
        case "paragraph" | "quote":
            return _sentences(node.text or "")
        case "bullets" | "post":
            return [i.strip() for i in (node.items or []) if len(i.strip()) >= MIN_CLAIM_CHARS]
        case "callout":
            parts = []
            if node.title:
                parts.append(node.title.strip())
            parts += _sentences(node.text or "")
            return [p for p in parts if len(p) >= MIN_CLAIM_CHARS]
        case "slide":
            parts = [i.strip() for i in (node.items or []) if len(i.strip()) >= MIN_CLAIM_CHARS]
            if node.notes:
                parts += _sentences(node.notes)
            return parts
        case "panel" | "scene":
            # Data points, captions and narration are claims. `notes` is visual
            # direction ("bar chart", "aerial shot") and states nothing; any
            # figure that strays into it is still caught by the consistency check.
            parts = [i.strip() for i in (node.items or []) if len(i.strip()) >= MIN_CLAIM_CHARS]
            parts += _sentences(node.text or "")
            return parts
        case "table":
            rows = node.rows or []
            # Skip the header row; a header states nothing.
            return [
                " ".join(c for c in row if c).strip()
                for row in rows[1:]
                if len(" ".join(row).strip()) >= MIN_CLAIM_CHARS
            ]
    return []


def atomize(ir: ContentIR) -> list[Claim]:
    claims: list[Claim] = []
    for node in ir.nodes:
        for text in _node_claims(node):
            claims.append(Claim(node_id=node.id, text=text, fact_ids=list(node.fact_ids)))
    return claims
