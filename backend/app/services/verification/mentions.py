"""Finding the checkable values inside generated text.

Deliberately conservative. A false alarm on demo day is worse than a missed
one, so anything ambiguous -- reference codes, clock times, version strings --
is skipped rather than guessed at.

Entities are left to the LLM layer; numbers and dates are where deterministic
checking is reliable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.services.sot.normalizer import (
    DMY_TEXT_RE,
    ISO_DATE_RE,
    MDY_TEXT_RE,
    SCALES,
    SLASH_DATE_RE,
    canonical_date,
    normalize_digits,
    parse_number,
)

DATE_PATTERNS = (ISO_DATE_RE, DMY_TEXT_RE, MDY_TEXT_RE, SLASH_DATE_RE)

# A bare number we are willing to check: digits, optional grouping/decimals.
NUMBER_TOKEN = re.compile(r"^[-+]?\d[\d,]*(?:\.\d+)?$")

# Characters that turn a numeric-looking token into something else entirely:
# CB/IR/2026/0412, AUTH-114, 02:14, v1.2.3, UTC+05:30.
DISQUALIFYING = re.compile(r"[A-Za-z/:]")

TRIM = " \t\n\r.,;:!?()[]{}\"'’“”*_#|"

SCALE_WORDS = {word for word, _ in SCALES}
PERCENT_WORDS = {"percent", "per", "%"}

MentionKind = Literal["number", "date"]


@dataclass(frozen=True, slots=True)
class Mention:
    raw: str
    canonical: str
    kind: MentionKind
    start: int
    end: int


def _date_spans(text: str) -> list[tuple[int, int, str, str]]:
    spans: list[tuple[int, int, str, str]] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            iso = canonical_date(match.group(0))
            if iso is None:
                continue
            # Longest match wins when patterns overlap.
            if any(match.start() < e and s < match.end() for s, e, _, _ in spans):
                continue
            spans.append((match.start(), match.end(), match.group(0), iso))
    return sorted(spans)


def extract_mentions(text: str) -> list[Mention]:
    """Every number and date in `text`, canonicalized for comparison."""
    if not text:
        return []
    source = normalize_digits(text)

    mentions: list[Mention] = []
    consumed: list[tuple[int, int]] = []

    for start, end, raw, iso in _date_spans(source):
        mentions.append(Mention(raw=raw, canonical=iso, kind="date", start=start, end=end))
        consumed.append((start, end))

    for match in re.finditer(r"\S+", source):
        token_start, token_end = match.span()
        # Skip anything already claimed by a date.
        if any(token_start < e and s < token_end for s, e in consumed):
            continue

        raw_token = match.group(0)
        lead = len(raw_token) - len(raw_token.lstrip(TRIM))
        cleaned = raw_token.strip(TRIM)
        if not cleaned or DISQUALIFYING.search(cleaned):
            continue

        # A trailing '%' survives the trim only when written as "62%".
        percent = cleaned.endswith("%")
        if percent:
            cleaned = cleaned[:-1]
        if not NUMBER_TOKEN.match(cleaned):
            continue

        # Look ahead for an Indian/Western scale word: "18.4 lakh".
        tail = source[token_end : token_end + 24].lstrip()
        next_word = tail.split(" ")[0].strip(TRIM).lower() if tail else ""
        phrase = f"{cleaned} {next_word}" if next_word in SCALE_WORDS else cleaned

        value = parse_number(phrase)
        if value is None:
            continue

        span_start = token_start + lead
        mentions.append(
            Mention(
                raw=phrase,
                canonical=_format(value),
                kind="number",
                start=span_start,
                end=span_start + len(cleaned),
            )
        )

    return sorted(mentions, key=lambda m: m.start)


def _format(value) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        return str(normalized.quantize(1))
    return format(normalized, "f")


def canonical_values(text: str) -> set[str]:
    return {m.canonical for m in extract_mentions(text)}
