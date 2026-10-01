"""A FormatSpec is the entire difference between one output type and another.

Adding another output type means adding one of these -- not a pipeline.

A spec may also declare its own options (slide count for a deck, duration for
a video). Each choice contributes a prompt line and may tighten the node
budget; `apply_options` folds them into a derived spec, so the generator
itself never knows options exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


@dataclass(frozen=True, slots=True)
class FormatChoice:
    key: str
    label: str
    # Added to the prompt when chosen. Empty means "no extra instruction".
    prompt_fragment: str = ""
    # Overrides the spec's node budget when chosen.
    max_nodes: int | None = None
    # Sets who the output is for (an audience key) when chosen, so a simple
    # "Presenting to" option can replace a separate audience picker.
    audience: str | None = None


@dataclass(frozen=True, slots=True)
class FormatOption:
    key: str
    label: str
    choices: tuple[FormatChoice, ...]
    default: str
    help: str = ""

    def choice(self, key: str) -> FormatChoice | None:
        return next((c for c in self.choices if c.key == key), None)


@dataclass(frozen=True, slots=True)
class FormatSpec:
    key: str
    name: str
    description: str
    # Node kinds the generator may emit. Anything else is rejected.
    allowed_kinds: tuple[str, ...]
    # Appended to the prompt; the only place format-specific wording lives.
    prompt_fragment: str
    renderers: tuple[str, ...]
    max_nodes: int = 40
    options: tuple[FormatOption, ...] = ()
    # Paragraphs up to this many words may skip citations: an email's greeting
    # and sign-off state nothing. 0 means every paragraph must cite a fact.
    uncited_max_words: int = 0
    # Audience and writing controls that suit this output when the user does
    # not choose them, e.g. {"audience": "public", "tone": "conversational"}.
    defaults: dict[str, str] = field(default_factory=dict)


class UnknownFormatOption(ValueError):
    pass


def resolve_options(spec: FormatSpec, values: dict[str, str] | None) -> dict[str, str]:
    """Fill in defaults and reject options or choices the spec does not declare."""
    declared = {o.key: o for o in spec.options}
    resolved = {o.key: o.default for o in spec.options}
    for key, value in (values or {}).items():
        option = declared.get(key)
        if option is None:
            raise UnknownFormatOption(f"{spec.name} has no option {key!r}")
        if option.choice(value) is None:
            allowed = ", ".join(c.key for c in option.choices)
            raise UnknownFormatOption(
                f"{option.label} cannot be {value!r} for {spec.name}. Choose from: {allowed}"
            )
        resolved[key] = value
    return resolved


def chosen_audience(spec: FormatSpec, values: dict[str, str] | None) -> str | None:
    """The audience implied by the chosen options, if any option sets one."""
    resolved = resolve_options(spec, values)
    for option in spec.options:
        choice = option.choice(resolved[option.key])
        if choice is not None and choice.audience:
            return choice.audience
    return None


def apply_options(spec: FormatSpec, values: dict[str, str] | None) -> FormatSpec:
    """A copy of the spec with the chosen options folded into prompt and budget."""
    if not spec.options:
        return spec
    resolved = resolve_options(spec, values)
    fragments: list[str] = []
    max_nodes = spec.max_nodes
    for option in spec.options:
        choice = option.choice(resolved[option.key])
        assert choice is not None  # guaranteed by resolve_options
        if choice.prompt_fragment:
            fragments.append(f"- {choice.prompt_fragment}")
        if choice.max_nodes is not None:
            max_nodes = choice.max_nodes
    if not fragments and max_nodes == spec.max_nodes:
        return spec
    prompt = spec.prompt_fragment
    if fragments:
        prompt += "\n\nOptions chosen for this output (they override the guidance above):\n"
        prompt += "\n".join(fragments)
    return replace(spec, prompt_fragment=prompt, max_nodes=max_nodes)
