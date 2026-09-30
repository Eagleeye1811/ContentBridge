"""A FormatSpec is the entire difference between one output type and another.

Adding an eighth output type means adding one of these -- not a pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass


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
