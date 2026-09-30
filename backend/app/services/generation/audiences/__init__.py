"""Audience profiles. Like formats, these are prompt configuration only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudienceProfile:
    key: str
    name: str
    prompt_fragment: str


AUDIENCES: dict[str, AudienceProfile] = {
    a.key: a
    for a in (
        AudienceProfile(
            "officer",
            "Officer",
            "Audience: a government officer. Formal, precise, decision-oriented. "
            "Expand acronyms on first use. No marketing tone, no hedging.",
        ),
        AudienceProfile(
            "management",
            "Management",
            "Audience: senior management. Lead with impact, cost and risk. "
            "Minimal technical detail; every paragraph should support a decision.",
        ),
        AudienceProfile(
            "technical",
            "Technical Team",
            "Audience: the technical team. Precise terminology is expected. "
            "Keep specifics: systems, controls, configurations, timelines.",
        ),
        AudienceProfile(
            "public",
            "Public",
            "Audience: the general public. Plain language, short sentences, no jargon. "
            "Explain why it matters to an ordinary reader. Never speculate.",
        ),
        AudienceProfile(
            "social",
            "Social Media",
            "Audience: social media readers. Very short, plain, scannable. "
            "No jargon, no alarm, no emoji unless the facts warrant emphasis.",
        ),
    )
}

LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi (Devanagari script)",
    "mr": "Marathi (Devanagari script)",
}


class UnknownAudience(ValueError):
    pass


def get_audience(key: str) -> AudienceProfile:
    profile = AUDIENCES.get(key)
    if profile is None:
        raise UnknownAudience(
            f"Unknown audience {key!r}. Available: {', '.join(sorted(AUDIENCES))}"
        )
    return profile


def language_name(code: str) -> str:
    return LANGUAGES.get(code, code)
