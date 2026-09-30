"""Canonicalization of values.

This module is the reason cross-output consistency is cheap: a number is
normalized exactly once, here, when the fact is born. Later phases compare
against `canonical_value` rather than diffing seven rendered documents.

It is deliberately dependency-free and pure so it can be tested hard.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

# Hindi/Marathi share the Devanagari digits; outputs in those languages must
# still compare equal to the English source.
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Indian numbering. Ordered longest-first so "crore" wins over "cr".
SCALES: list[tuple[str, Decimal]] = [
    ("crore", Decimal(10_000_000)),
    ("karod", Decimal(10_000_000)),
    ("lakh", Decimal(100_000)),
    ("lac", Decimal(100_000)),
    ("million", Decimal(1_000_000)),
    ("billion", Decimal(1_000_000_000)),
    ("thousand", Decimal(1_000)),
    ("cr", Decimal(10_000_000)),
    ("mn", Decimal(1_000_000)),
    ("bn", Decimal(1_000_000_000)),
    ("k", Decimal(1_000)),
]

MONTHS = {
    m: i
    for i, names in enumerate(
        [
            ("january", "jan"),
            ("february", "feb"),
            ("march", "mar"),
            ("april", "apr"),
            ("may",),
            ("june", "jun"),
            ("july", "jul"),
            ("august", "aug"),
            ("september", "sep", "sept"),
            ("october", "oct"),
            ("november", "nov"),
            ("december", "dec"),
        ],
        start=1,
    )
    for m in names
}

NUMBER_RE = re.compile(r"[-+]?\d[\d,\s]*(?:\.\d+)?")
PERCENT_RE = re.compile(r"(?:%|\bper\s?cent\b|\bpercent\b)", re.IGNORECASE)
CURRENCY_RE = re.compile(r"(?:₹|\bINR\b|\brupees?\b|\bRs\.?\b|\$|\bUSD\b)", re.IGNORECASE)

ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DMY_TEXT_RE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})\b",
)
MDY_TEXT_RE = re.compile(
    r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b",
)
SLASH_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")


def normalize_digits(text: str) -> str:
    """Devanagari digits to ASCII, so cross-language values compare equal."""
    return text.translate(DEVANAGARI_DIGITS)


def _to_decimal(raw: str) -> Decimal | None:
    cleaned = re.sub(r"[,\s]", "", raw)
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_number(text: str) -> Decimal | None:
    """First number in `text`, with an Indian/Western scale word applied."""
    if not text:
        return None
    source = normalize_digits(text)
    match = NUMBER_RE.search(source)
    if not match:
        return None
    value = _to_decimal(match.group(0))
    if value is None:
        return None

    tail = source[match.end() :].lower()
    for word, factor in SCALES:
        # Only a scale word immediately following the number counts.
        if re.match(rf"\s*{re.escape(word)}\b", tail):
            return value * factor
    return value


def _format(value: Decimal) -> str:
    """Stable string form: integral values lose the decimal point."""
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f")


def canonical_number(text: str) -> str | None:
    value = parse_number(text)
    return None if value is None else _format(value)


def canonical_date(text: str) -> str | None:
    """ISO-8601 for the first date found, or None."""
    if not text:
        return None
    source = normalize_digits(text)

    if m := ISO_DATE_RE.search(source):
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if m := DMY_TEXT_RE.search(source):
        month = MONTHS.get(m.group(2).lower())
        if month:
            return _safe_date(int(m.group(3)), month, int(m.group(1)))
    if m := MDY_TEXT_RE.search(source):
        month = MONTHS.get(m.group(1).lower())
        if month:
            return _safe_date(int(m.group(3)), month, int(m.group(2)))
    if m := SLASH_DATE_RE.search(source):
        # Day-first: this is an Indian government context.
        return _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def detect_unit(text: str) -> str | None:
    if PERCENT_RE.search(text):
        return "percent"
    if CURRENCY_RE.search(text):
        return "currency"
    return None


def canonicalize(
    raw_value: str | None, statement: str, fact_type: str
) -> tuple[str | None, str | None]:
    """Return `(canonical_value, unit)` for a fact.

    `raw_value` is what the model reported; `statement` is the sentence it came
    from, used as a fallback and to detect units the model omitted.
    """
    source = (raw_value or "").strip()
    context = f"{source} {statement}".strip()

    if fact_type == "date":
        return canonical_date(source) or canonical_date(statement), None

    unit = detect_unit(source) or detect_unit(statement)

    number = canonical_number(source) if source else None
    if number is None:
        # The model may have given a phrase rather than a figure.
        number = canonical_number(statement)

    if number is None:
        # Non-numeric facts (findings, recommendations) canonicalize to their
        # own trimmed text so they still compare across outputs.
        if fact_type in {"metric", "date"}:
            return None, unit
        return (source or None), unit

    if unit == "currency" and "currency" not in context.lower():
        unit = "currency"
    return number, unit


def slugify_key(text: str, *, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_digits(text).lower()).strip("_")
    return slug[:max_length].strip("_") or "fact"
