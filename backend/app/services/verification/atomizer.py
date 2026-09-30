"""Splitting generated content into atomic, checkable claims."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.content_ir import ContentIR, Node

# Split on sentence punctuation followed by whitespace and a capital/digit,
# which leaves "e.g." and "No. 4" alone in the common cases.
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Zऀ-ॿ0-9])")
MIN_CLAIM_CHARS = 12


@dataclass(slots=True)
class Claim:
    node_id: str
    text: str
    fact_ids: list[str]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE.split(text.strip()) if len(s.strip()) >= MIN_CLAIM_CHARS]


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
