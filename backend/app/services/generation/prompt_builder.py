"""Prompt assembly.

Exactly one prompt shape exists. An output type contributes a fragment; an
audience contributes a fragment; a language contributes a line. Nothing else
differs between an advisory and a press release.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol

from app.services.generation.audiences import AudienceProfile, language_name
from app.services.generation.formats.base import FormatSpec


class FactLike(Protocol):
    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None


SYSTEM = """You write official communications from a verified Source of Truth.

Hard rules:
- Use ONLY the facts provided. If something is not in the facts, it does not go
  in the output, however natural it would sound.
- Every node MUST list the fact labels it was built from in `fact_ids`, using
  the exact labels shown (for example f2). A sentence you cannot attribute is a
  sentence you must not write.
- Reproduce every number, date and proper noun EXACTLY as the fact states it.
  Never round, convert, re-scale or reformat a figure.
- Never add a recommendation, cause, severity or consequence that the facts do
  not state.
- Use only the node kinds you are told are allowed.
- Give every node a short unique `id` such as n1, n2, n3.
"""


def render_facts(facts: Sequence[FactLike]) -> tuple[str, dict[str, FactLike]]:
    """Label facts f0..fN.

    Short labels keep the prompt small and make an invented citation obvious:
    the model is never shown a real UUID, so it cannot guess one.
    """
    label_map: dict[str, FactLike] = {}
    lines: list[str] = []
    for i, fact in enumerate(facts):
        label = f"f{i}"
        label_map[label] = fact
        bits = [fact.type]
        if fact.canonical_value is not None:
            bits.append(f"value={fact.canonical_value}")
        if fact.unit:
            bits.append(f"unit={fact.unit}")
        lines.append(f"[{label}] ({', '.join(bits)}) {fact.statement}")
    return "\n".join(lines), label_map


def build_prompt(
    *,
    facts: Sequence[FactLike],
    spec: FormatSpec,
    audience: AudienceProfile,
    language: str,
    source_name: str,
    violations: Sequence[str] = (),
) -> tuple[str, dict[str, FactLike]]:
    fact_block, label_map = render_facts(facts)

    sections = [
        f"SOURCE DOCUMENT: {source_name}",
        "",
        "FACTS (the only permitted source of content):",
        fact_block,
        "",
        spec.prompt_fragment,
        "",
        audience.prompt_fragment,
        "",
        f"Allowed node kinds: {', '.join(spec.allowed_kinds)}",
        f"Maximum nodes: {spec.max_nodes}",
        f"Write the output in {language_name(language)}.",
    ]

    if language != "en":
        sections.append(
            "Keep all digits in Latin numerals and keep proper nouns, reference "
            "numbers and units exactly as they appear in the facts."
        )

    if violations:
        # A second attempt gets told precisely what it got wrong.
        sections += [
            "",
            "Your previous attempt was rejected. Fix these problems exactly:",
            *(f"- {v}" for v in violations),
        ]

    return "\n".join(sections), label_map
