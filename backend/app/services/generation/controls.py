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
        "concise",
        "Concise",
        "Focus on key message and essential facts; short bullets & compact visual summaries.",
        "Detail level: concise. Focus strictly on the core message and essential key facts. Use short, high-impact bullet fragments and compact visual summaries. Minimize supporting explanation.",
    ),
    ControlOption(
        "brief",
        "Brief (Concise)",
        "Alias for concise.",
        "Detail level: concise. Focus strictly on the core message and essential key facts. Use short, high-impact bullet fragments and compact visual summaries. Minimize supporting explanation.",
    ),
    ControlOption(
        "balanced",
        "Balanced",
        "Key message, supporting facts, brief explanation of significance, context, metrics.",
        "Detail level: balanced. Include the key message, relevant supporting facts, and a brief explanation of significance. Use a mix of bullets, metrics, timelines, diagrams, and concise explanatory text.",
    ),
    ControlOption(
        "standard",
        "Standard (Balanced)",
        "Alias for balanced.",
        "Detail level: balanced. Include the key message, relevant supporting facts, and a brief explanation of significance. Use a mix of bullets, metrics, timelines, diagrams, and concise explanatory text.",
    ),
    ControlOption(
        "detailed",
        "Detailed",
        "Fuller explanations, relevant context, evidence, implications, relationships, tables.",
        "Detail level: detailed. Include fuller explanations, relevant context, evidence, and implications. Explain important relationships between findings and their consequences. Include additional source-supported details, qualifications, and unresolved questions.",
    ),
    ControlOption(
        "comprehensive",
        "Comprehensive (Detailed)",
        "Alias for detailed.",
        "Detail level: detailed. Include fuller explanations, relevant context, evidence, and implications. Explain important relationships between findings and their consequences. Include additional source-supported details, qualifications, and unresolved questions.",
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

PURPOSES = _registry(
    ControlOption(
        "executive briefing",
        "Executive Briefing",
        "Lead with decision required, key findings, financial implications, risks, and next actions.",
        "Presentation purpose: Executive Briefing. Lead with key decision required, main findings, financial impact, risk mitigation, and clear next steps.",
    ),
    ControlOption(
        "technical briefing",
        "Technical Briefing",
        "Architecture, implementation details, dependencies, constraints, technical trade-offs.",
        "Presentation purpose: Technical Briefing. Focus on architecture, technical dependencies, exact system parameters, trade-offs, and operational requirements.",
    ),
    ControlOption(
        "research/findings",
        "Research / Findings",
        "Emphasize research questions, methodology, findings, evidence, limitations, and implications.",
        "Presentation purpose: Research / Findings. Focus on core findings, empirical evidence, data points, research limitations, and key analytical takeaways.",
    ),
    ControlOption(
        "public awareness",
        "Public Awareness",
        "Accessible language, practical implications, avoiding jargon.",
        "Presentation purpose: Public Awareness. Use clear accessible phrasing, explain technical terms, emphasize real-world impact, and avoid jargon.",
    ),
    ControlOption(
        "project proposal",
        "Project Proposal",
        "Problem, objectives, proposed solution, scope, roadmap, budget, risks, metrics, decisions.",
        "Presentation purpose: Project Proposal. Structure around problem statement, objectives, solution scope, implementation roadmap, risk analysis, and required decisions.",
    ),
    ControlOption(
        "training",
        "Training",
        "Learning objectives, concepts, examples, practical steps, recap questions.",
        "Presentation purpose: Training. Structure around learning objectives, clear step-by-step explanations, practical examples, and summary takeaways.",
    ),
)

DURATIONS = _registry(
    ControlOption(
        "5",
        "5 minutes",
        "Short briefing.",
        "Presentation duration: 5 minutes. High-density pacing: focus strictly on essential takeaways.",
    ),
    ControlOption(
        "10",
        "10 minutes",
        "Standard briefing.",
        "Presentation duration: 10 minutes. Standard briefing pacing with key findings and action items.",
    ),
    ControlOption(
        "15",
        "15 minutes",
        "Extended presentation.",
        "Presentation duration: 15 minutes. Moderate pacing with full supporting context, evidence, and clear transitions.",
    ),
    ControlOption(
        "30",
        "30 minutes",
        "In-depth workshop/briefing.",
        "Presentation duration: 30 minutes. Comprehensive pacing with detailed analysis, comparative trade-offs, risk analysis, and complete roadmap.",
    ),
)

VISUAL_PREFERENCES = _registry(
    ControlOption(
        "text-focused",
        "Text-focused",
        "Structured text, clear section lists, tables.",
        "Visual preference: text-focused. Use clean structured bullet points, two-column split cards, and data tables.",
    ),
    ControlOption(
        "balanced",
        "Balanced",
        "Mix of bullet text, KPI cards, process diagrams, timelines, tables.",
        "Visual preference: balanced. Use a harmonious mix of bullet lists, KPI metric cards, process flows, timelines, and comparison columns.",
    ),
    ControlOption(
        "visual-heavy",
        "Visual-heavy",
        "Diagrams, timelines, process flows, KPI metric cards.",
        "Visual preference: visual-heavy. Maximize visual structures: use process flow cards, timeline nodes, prominent KPI metric cards, visual comparison columns, and structured tables over plain bullet text.",
    ),
)

EXTRA_CONTROL_REGISTRIES: dict[str, dict[str, ControlOption]] = {
    "purpose": PURPOSES,
    "duration": DURATIONS,
    "visual_preference": VISUAL_PREFERENCES,
}

# The dimension name as it appears on requests and on stored outputs.
CONTROL_REGISTRIES: dict[str, dict[str, ControlOption]] = {
    "tone": TONES,
    "detail_level": DETAIL_LEVELS,
    "objective": OBJECTIVES,
    "style": STYLES,
}

ALIAS_MAP: dict[str, dict[str, str]] = {
    "detail_level": {
        "brief": "concise",
        "standard": "balanced",
        "comprehensive": "detailed",
    }
}

DEFAULT_CONTROLS: dict[str, str] = {
    "tone": "formal",
    "detail_level": "balanced",
    "objective": "inform",
    "style": "structured",
}


class UnknownControl(ValueError):
    pass


def resolve_controls(values: dict[str, str] | None) -> dict[str, str]:
    """Fill in defaults and reject anything not in a registry."""
    resolved = dict(DEFAULT_CONTROLS)
    PASSTHROUGH_KEYS = ("theme", "format", "slide_count", "additional_instructions", "speaker_notes")
    for name, raw_value in (values or {}).items():
        if name in PASSTHROUGH_KEYS:
            resolved[name] = str(raw_value)
            continue
        registry = CONTROL_REGISTRIES.get(name) or EXTRA_CONTROL_REGISTRIES.get(name)
        if registry is None:
            raise UnknownControl(f"Unknown control {name!r}")
        value = ALIAS_MAP.get(name, {}).get(raw_value, raw_value)
        if value not in registry:
            raise UnknownControl(
                f"Unknown {name.replace('_', ' ')} {raw_value!r}. "
                f"Available: {', '.join(sorted(registry))}"
            )
        resolved[name] = value
    return resolved


def control_fragments(values: dict[str, str] | None) -> list[str]:
    resolved = resolve_controls(values)
    all_registries = {**CONTROL_REGISTRIES, **EXTRA_CONTROL_REGISTRIES}
    fragments = []
    for name in all_registries:
        if name in resolved and resolved[name] in all_registries[name]:
            fragments.append(all_registries[name][resolved[name]].prompt_fragment)
    return fragments

