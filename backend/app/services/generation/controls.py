"""Communication controls: tone, detail level, objective and content style.

Like audiences, these are prompt configuration only. Each one contributes a
fragment; none of them is allowed to change a fact. The generator, validation
and verification are identical whatever is chosen here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControlOption:
    key: str
    name: str
    description: str
    prompt_fragment: str


def _registry(*options: ControlOption) -> dict[str, ControlOption]:
    return {o.key: o for o in options}


TONES = _registry(
    ControlOption(
        "formal",
        "Formal",
        "Official, impersonal register.",
        "Tone: formal and official. Impersonal constructions, no contractions.",
    ),
    ControlOption(
        "neutral",
        "Neutral",
        "Plain and matter-of-fact.",
        "Tone: neutral and matter-of-fact. No emphasis beyond what the facts carry.",
    ),
    ControlOption(
        "urgent",
        "Urgent",
        "Direct and time-sensitive.",
        "Tone: urgent and direct. Lead with what must happen and by when, using only "
        "deadlines and actions the facts state. Never exaggerate a risk to create urgency.",
    ),
    ControlOption(
        "empathetic",
        "Empathetic",
        "Considerate of those affected.",
        "Tone: empathetic. Acknowledge the people affected and speak to them with care, "
        "without softening any finding or offering comfort the facts do not support.",
    ),
    ControlOption(
        "conversational",
        "Conversational",
        "Approachable, second person.",
        "Tone: conversational. Address the reader directly, short sentences, everyday "
        "words, while keeping every figure exact.",
    ),
)

DETAIL_LEVELS = _registry(
    ControlOption(
        "brief",
        "Brief",
        "Only the essentials.",
        "Detail level: brief. Keep only the most important facts and use well under the "
        "maximum number of nodes.",
    ),
    ControlOption(
        "standard",
        "Standard",
        "Balanced coverage.",
        "Detail level: standard. Cover the key facts with enough context to act on them.",
    ),
    ControlOption(
        "comprehensive",
        "Comprehensive",
        "Every supported point.",
        "Detail level: comprehensive. Cover every relevant fact the format allows, but "
        "never pad a section the facts cannot fill.",
    ),
)

OBJECTIVES = _registry(
    ControlOption(
        "inform",
        "Inform",
        "Explain what happened.",
        "Communication objective: inform. Make the reader understand what happened and "
        "what it means.",
    ),
    ControlOption(
        "alert",
        "Alert",
        "Warn about a risk.",
        "Communication objective: alert. Put the risk and its scope first, then what is "
        "being done about it.",
    ),
    ControlOption(
        "instruct",
        "Instruct",
        "Drive specific actions.",
        "Communication objective: instruct. Centre the output on the actions the facts "
        "recommend, stated as clear steps. Do not invent steps.",
    ),
    ControlOption(
        "awareness",
        "Build awareness",
        "Educate a wider audience.",
        "Communication objective: build awareness. Explain why this matters to the "
        "audience, using only the facts as evidence.",
    ),
    ControlOption(
        "record",
        "Record",
        "Document for the archive.",
        "Communication objective: record. Prioritise completeness, dates and references "
        "so the output can stand as the record.",
    ),
)

STYLES = _registry(
    ControlOption(
        "structured",
        "Structured",
        "Scannable sections and lists.",
        "Content style: structured. Prefer short sections, lists and labelled points "
        "where the format allows them.",
    ),
    ControlOption(
        "narrative",
        "Narrative",
        "Flowing, connected prose.",
        "Content style: narrative. Connect the facts into flowing prose in a logical "
        "order, where the format allows prose.",
    ),
    ControlOption(
        "data_driven",
        "Data-driven",
        "Lead with the figures.",
        "Content style: data-driven. Lead each point with its figure, date or metric "
        "from the facts.",
    ),
    ControlOption(
        "plain_language",
        "Plain language",
        "Simple words, no jargon.",
        "Content style: plain language. Everyday words, no jargon, one idea per sentence.",
    ),
)

# The dimension name as it appears on requests and on stored outputs.
CONTROL_REGISTRIES: dict[str, dict[str, ControlOption]] = {
    "tone": TONES,
    "detail_level": DETAIL_LEVELS,
    "objective": OBJECTIVES,
    "style": STYLES,
}

DEFAULT_CONTROLS: dict[str, str] = {
    "tone": "formal",
    "detail_level": "standard",
    "objective": "inform",
    "style": "structured",
}


class UnknownControl(ValueError):
    pass


def resolve_controls(values: dict[str, str] | None) -> dict[str, str]:
    """Fill in defaults and reject anything not in a registry."""
    resolved = dict(DEFAULT_CONTROLS)
    for name, value in (values or {}).items():
        registry = CONTROL_REGISTRIES.get(name)
        if registry is None:
            raise UnknownControl(f"Unknown control {name!r}")
        if value not in registry:
            raise UnknownControl(
                f"Unknown {name.replace('_', ' ')} {value!r}. "
                f"Available: {', '.join(sorted(registry))}"
            )
        resolved[name] = value
    return resolved


def control_fragments(values: dict[str, str] | None) -> list[str]:
    resolved = resolve_controls(values)
    return [CONTROL_REGISTRIES[name][resolved[name]].prompt_fragment for name in CONTROL_REGISTRIES]
