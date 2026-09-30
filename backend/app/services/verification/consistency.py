"""Layer 1: deterministic cross-output consistency.

No LLM. Because every output cites the same fact ids, and values were
canonicalized once when the fact was born, checking agreement is a string
comparison rather than a seven-way diff of rendered documents.

This layer is instant, free, and cannot flake in front of an audience.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.content_ir import ContentIR, iter_text
from app.services.sot.normalizer import normalize_digits, parse_number
from app.services.verification.mentions import extract_mentions


class FactLike(Protocol):
    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None


@dataclass(slots=True)
class Cell:
    """What one output stated for one fact."""

    output_id: str
    stated: str | None = None
    agrees: bool | None = None  # None when the output cites the fact but states no figure
    snippet: str = ""


@dataclass(slots=True)
class MatrixRow:
    fact_id: str
    key: str
    statement: str
    expected: str | None
    unit: str | None
    cells: list[Cell] = field(default_factory=list)

    @property
    def has_mismatch(self) -> bool:
        return any(c.agrees is False for c in self.cells)


@dataclass(slots=True)
class Unsourced:
    """A figure in an output that belongs to no fact in the Source of Truth."""

    output_id: str
    value: str
    snippet: str


@dataclass(slots=True)
class Analysis:
    rows: list[MatrixRow]
    unsourced: list[Unsourced]

    @property
    def mismatches(self) -> list[MatrixRow]:
        return [r for r in self.rows if r.has_mismatch]


def _kind_of(value: str) -> str:
    return "date" if "-" in value and len(value) == 10 else "number"


DIGIT_RUN = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _literal_values(text: str) -> set[str]:
    """Every digit run in the text, canonicalized.

    A figure can be present without surfacing as a Mention -- "11" inside
    "11 March 2026" is consumed by the date, and "00" inside "11:00" is
    skipped as a clock time. Treating those as absent produces false alarms,
    so this is the weaker check that suppresses them.
    """
    values: set[str] = set()
    for match in DIGIT_RUN.finditer(normalize_digits(text)):
        parsed = parse_number(match.group(0))
        if parsed is not None:
            values.add(_format_decimal(parsed))
    return values


def _format_decimal(value) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(1))
    return format(normalized, "f")


def analyze(
    facts: Sequence[FactLike],
    outputs: Sequence[tuple[str, ContentIR]],
) -> Analysis:
    """Build the facts x outputs matrix and collect unsourced figures."""
    by_id = {str(f.id): f for f in facts}
    checkable = {fid: f for fid, f in by_id.items() if f.canonical_value}

    # Anything the Source of Truth knows about, in canonical form.
    sheet_values: set[str] = {f.canonical_value for f in facts if f.canonical_value}
    for f in facts:
        sheet_values |= {m.canonical for m in extract_mentions(f.statement)}

    rows = {
        fid: MatrixRow(
            fact_id=fid,
            key=f.key,
            statement=f.statement,
            expected=f.canonical_value,
            unit=f.unit,
        )
        for fid, f in checkable.items()
    }

    unsourced: list[Unsourced] = []

    for output_id, ir in outputs:
        stated: dict[str, Cell] = {}
        seen_unsourced: set[str] = set()

        for node in ir.nodes:
            text = " ".join(iter_text(node))
            if not text.strip():
                continue
            mentions = extract_mentions(text)
            found = {m.canonical for m in mentions}

            cited = [fid for fid in node.fact_ids if fid in checkable]
            cited_expected = {checkable[fid].canonical_value for fid in cited}
            literal = _literal_values(text)

            # Mentions that no cited fact accounts for. A disagreement can only
            # be attributed to a fact when exactly one of these could be it.
            spare = [m for m in mentions if m.canonical not in cited_expected]

            for fid in cited:
                fact = checkable[fid]
                expected = fact.canonical_value
                assert expected is not None

                if fid in stated and stated[fid].agrees:
                    continue

                if expected in found or expected in literal:
                    # Agreement wins: once an output states the right value for
                    # a fact, a stray number elsewhere in the node is not a
                    # contradiction of that fact.
                    stated[fid] = Cell(output_id, expected, True, _clip(text))
                    continue

                # Only claim a mismatch when attribution is unambiguous. With
                # several unaccounted figures we cannot tell which one was
                # meant to be this fact, and guessing produces false alarms.
                candidates = [m for m in spare if m.kind == _kind_of(expected)]
                if len(candidates) == 1:
                    stated[fid] = Cell(output_id, candidates[0].canonical, False, _clip(text))
                else:
                    stated.setdefault(fid, Cell(output_id, None, None, _clip(text)))

            # A figure that matches nothing in the sheet, and is not written in
            # any fact this node cites, was invented somewhere.
            cited_text = " ".join(
                normalize_digits(by_id[fid].statement) for fid in node.fact_ids if fid in by_id
            )
            for mention in mentions:
                if mention.canonical in sheet_values:
                    continue
                if mention.raw in cited_text:
                    continue
                if mention.canonical in seen_unsourced:
                    continue
                seen_unsourced.add(mention.canonical)
                unsourced.append(Unsourced(output_id, mention.canonical, _clip(text)))

        for fid, cell in stated.items():
            rows[fid].cells.append(cell)

    # A row where no output stated anything is noise in the matrix.
    ordered = [r for r in rows.values() if any(c.stated is not None for c in r.cells)]
    ordered.sort(key=lambda r: (not r.has_mismatch, r.key))
    return Analysis(rows=ordered, unsourced=unsourced)


def _clip(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
