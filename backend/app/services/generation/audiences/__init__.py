"""Audience profiles and languages.

Like formats, these are prompt configuration only. An audience changes register
and emphasis; it must never change a fact.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudienceProfile:
    key: str
    name: str
    prompt_fragment: str


_SHARED = (
    "Changing audience changes register and emphasis only. Never drop a figure, "
    "soften a finding, or add reassurance the facts do not support."
)

AUDIENCES: dict[str, AudienceProfile] = {
    a.key: a
    for a in (
        AudienceProfile(
            "officer",
            "Officer",
            "Audience: a government officer acting on this.\n"
            "- Formal, precise, impersonal. Full sentences.\n"
            "- Expand every acronym on first use, then use the short form.\n"
            "- Keep reference numbers, dates and designations exactly as written.\n"
            "- Lead each section with the operative point, not with background.\n"
            f"- {_SHARED}",
        ),
        AudienceProfile(
            "management",
            "Management",
            "Audience: senior management deciding what to do.\n"
            "- Lead with impact, cost, risk and the decision being asked for.\n"
            "- Minimal technical detail: name a system only when the decision "
            "turns on it.\n"
            "- Short paragraphs. Every one should support a decision.\n"
            f"- {_SHARED}",
        ),
        AudienceProfile(
            "technical",
            "Technical Team",
            "Audience: the engineers who will implement the response.\n"
            "- Precise terminology is expected; do not expand common technical "
            "acronyms.\n"
            "- Keep specifics: systems, controls, configurations, versions, "
            "timestamps.\n"
            "- Prefer concrete steps over intent.\n"
            f"- {_SHARED}",
        ),
        AudienceProfile(
            "public",
            "Public",
            "Audience: a member of the public with no background in this.\n"
            "- Plain language. Short sentences. No jargon and no acronyms.\n"
            "- Say what it means for an ordinary reader and what, if anything, "
            "they should do.\n"
            "- Do not speculate, reassure or alarm. State only what is confirmed.\n"
            f"- {_SHARED}",
        ),
        AudienceProfile(
            "social",
            "Social Media",
            "Audience: someone scrolling past.\n"
            "- Very short and scannable. One idea per line.\n"
            "- No jargon, no acronyms, no emoji.\n"
            "- Calm and factual. Never sensationalise a finding to gain attention.\n"
            f"- {_SHARED}",
        ),
    )
}

LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi (Devanagari script)",
    "mr": "Marathi (Devanagari script)",
}

# Languages whose output must actually be written in Devanagari. Asking for
# Marathi and silently receiving English is a failure worth catching.
DEVANAGARI_LANGUAGES = frozenset({"hi", "mr"})


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
