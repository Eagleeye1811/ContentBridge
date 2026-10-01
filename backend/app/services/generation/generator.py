"""The single generator.

Advisory, summary, deck, email, LinkedIn post, press release, report,
infographic package and video package all come through this function. They
differ only by the FormatSpec handed in.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.config import settings
from app.schemas.content_ir import ContentIR, DraftIR, Node, iter_text
from app.services.generation.audiences import (
    DEVANAGARI_LANGUAGES,
    AudienceProfile,
    language_name,
)
from app.services.generation.formats.base import FormatSpec
from app.services.generation.prompt_builder import SYSTEM, FactLike, build_prompt
from app.services.llm import get_llm

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

DEVANAGARI = re.compile(r"[\u0900-\u097F]")


# The field each kind cannot do without, and how many entries it needs. A slide
# whose text all landed in speaker notes renders as an empty slide.
REQUIRED_CONTENT: dict[str, tuple[str, int]] = {
    "slide": ("items", 2),
    "bullets": ("items", 1),
    "post": ("items", 1),
    "panel": ("items", 1),
    "scene": ("text", 1),
    "paragraph": ("text", 1),
    "quote": ("text", 1),
}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?\u0964])\s+")


def _uncited_ok(node: Node, spec: FormatSpec) -> bool:
    """Headings never need a citation; a spec may also allow short paragraphs."""
    if node.kind == "heading":
        return True
    return (
        spec.uncited_max_words > 0
        and node.kind == "paragraph"
        and len((node.text or "").split()) <= spec.uncited_max_words
    )


def _content_count(node: Node, field_name: str) -> int:
    value = getattr(node, field_name)
    if field_name == "items":
        return len([i for i in (value or []) if i and i.strip()])
    return 1 if value and value.strip() else 0


class GenerationError(RuntimeError):
    pass


@dataclass(slots=True)
class GenerationResult:
    content_ir: ContentIR
    model: str
    dropped_citations: list[str] = field(default_factory=list)
    attempts: int = 1


def _validate(ir: ContentIR, spec: FormatSpec, labels: set[str], language: str = "en") -> list[str]:
    """Structural problems worth a retry, phrased so a model can act on them."""
    problems: list[str] = []

    if not ir.nodes:
        problems.append("The output had no nodes. Produce the structure described above.")
    if len(ir.nodes) > spec.max_nodes:
        problems.append(
            f"You produced {len(ir.nodes)} nodes but at most {spec.max_nodes} are allowed."
        )

    allowed = set(spec.allowed_kinds)
    for node in ir.nodes:
        if node.kind not in allowed:
            problems.append(
                f"Node {node.id!r} used kind {node.kind!r}, which is not allowed here. "
                f"Allowed kinds: {', '.join(sorted(allowed))}."
            )
        unknown = [label for label in node.fact_ids if label not in labels]
        if unknown:
            problems.append(
                f"Node {node.id!r} cited {', '.join(repr(u) for u in unknown)}, which "
                "do not exist. Cite only the labels listed in FACTS."
            )
        if spec.max_node_chars:
            length = len("\n".join(iter_text(node)))
            if length > spec.max_node_chars:
                problems.append(
                    f"Node {node.id!r} is {length} characters; each must be at most "
                    f"{spec.max_node_chars}. Shorten it."
                )
        required = REQUIRED_CONTENT.get(node.kind)
        if required and _content_count(node, required[0]) < required[1]:
            field_name, minimum = required
            problems.append(
                f"Node {node.id!r} ({node.kind}) has too little in `{field_name}`: it needs "
                f"at least {minimum} entr{'ies' if minimum > 1 else 'y'}. Put the visible "
                f"content in `{field_name}`, not only in `notes`."
            )
        if node.kind == "heading" and not (node.text or node.title or "").strip():
            problems.append(f"Node {node.id!r} is a heading with no text. Give it `text`.")
        if not node.fact_ids and not _uncited_ok(node, spec):
            # Headings are navigational; everything else must be attributable.
            problems.append(
                f"Node {node.id!r} cited no facts. Every non-heading node must cite at "
                "least one fact label."
            )

    # Asking for Marathi and silently receiving English is a failure the
    # reviewer would have to notice by eye. Catch it here instead.
    if language in DEVANAGARI_LANGUAGES and ir.nodes:
        body = " ".join(t for node in ir.nodes for t in iter_text(node))
        if body.strip() and not DEVANAGARI.search(body):
            problems.append(
                f"The output must be written in {language_name(language)}, but it "
                "contains no Devanagari text. Rewrite the entire output in that "
                "language, keeping digits, reference numbers and proper nouns as they "
                "appear in the facts."
            )

    return problems


def _sanitize(
    ir: ContentIR, spec: FormatSpec, label_map: dict[str, FactLike]
) -> tuple[ContentIR, list[str]]:
    """Last line of defence: drop what is still wrong and remap labels to ids.

    Retrying is preferred, but a stubborn model must not be able to put an
    unattributable claim in front of a reviewer.
    """
    allowed = set(spec.allowed_kinds)
    dropped: list[str] = []
    nodes: list[Node] = []
    seen_ids: set[str] = set()

    for index, node in enumerate(ir.nodes):
        if node.kind not in allowed:
            dropped.append(f"node {node.id!r} (disallowed kind {node.kind!r})")
            continue

        resolved: list[str] = []
        for label in node.fact_ids:
            fact = label_map.get(label)
            if fact is None:
                dropped.append(f"citation {label!r} on node {node.id!r}")
                continue
            resolved.append(str(fact.id))

        if not resolved and not _uncited_ok(node, spec):
            dropped.append(f"node {node.id!r} (no resolvable citation)")
            continue

        # Headings carry their words in `text`; accept a stray `title`, drop empties.
        if node.kind == "heading":
            words = (node.text or node.title or "").strip()
            if not words:
                dropped.append(f"node {node.id!r} (empty heading)")
                continue
            node = node.model_copy(update={"text": words})

        # A slide that put everything in its notes: show the notes as bullets
        # rather than an empty slide.
        if node.kind == "slide" and _content_count(node, "items") == 0 and node.notes:
            bullets = [p.strip() for p in SENTENCE_SPLIT.split(node.notes) if p.strip()]
            node = node.model_copy(update={"items": bullets, "notes": None})

        required = REQUIRED_CONTENT.get(node.kind)
        if required and _content_count(node, required[0]) == 0:
            dropped.append(f"node {node.id!r} (empty {node.kind})")
            continue

        # Node ids must be unique for the editor and for verification anchoring.
        node_id = node.id or f"n{index}"
        while node_id in seen_ids:
            node_id = f"{node_id}_{index}"
        seen_ids.add(node_id)

        nodes.append(node.model_copy(update={"id": node_id, "fact_ids": resolved}))

    return ContentIR(title=ir.title, nodes=nodes[: spec.max_nodes]), dropped


async def generate(
    *,
    facts: Sequence[FactLike],
    spec: FormatSpec,
    audience: AudienceProfile,
    language: str,
    source_name: str,
    controls: dict[str, str] | None = None,
) -> GenerationResult:
    if not facts:
        raise GenerationError("Cannot generate from an empty Source of Truth. Extract facts first.")

    llm = get_llm()
    violations: list[str] = []
    last: ContentIR | None = None
    label_map: dict[str, FactLike] = {}
    attempts_used = 0

    for attempt in range(1, MAX_ATTEMPTS + 1):
        attempts_used = attempt
        prompt, label_map = build_prompt(
            facts=facts,
            spec=spec,
            audience=audience,
            language=language,
            source_name=source_name,
            controls=controls,
            violations=violations,
        )
        draft = await llm.complete_structured(system=SYSTEM, prompt=prompt, schema=DraftIR)
        last = draft.to_content_ir()

        violations = _validate(last, spec, set(label_map), language)
        if not violations:
            break
        log.warning(
            "generation attempt %d for %s rejected: %s", attempt, spec.key, "; ".join(violations)
        )

    if last is None:  # pragma: no cover - loop always assigns
        raise GenerationError("Generation produced no result")

    if any("Devanagari" in v for v in violations):
        # Shipping English labelled as Marathi is worse than shipping nothing;
        # the caller records this per combination and carries on with the rest.
        raise GenerationError(
            f"Generation for {spec.key} did not produce {language_name(language)} text."
        )

    content_ir, dropped = _sanitize(last, spec, label_map)
    if not content_ir.nodes:
        raise GenerationError(
            f"Generation for {spec.key} produced nothing attributable to the Source of Truth."
        )

    return GenerationResult(
        content_ir=content_ir,
        model=settings.llm_model if settings.llm_provider != "stub" else "stub",
        dropped_citations=dropped,
        attempts=attempts_used,
    )
