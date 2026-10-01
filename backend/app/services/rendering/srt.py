"""ContentIR -> SubRip subtitles for a video package.

Subtitles are derived from each scene's narration rather than written
separately, so they can never say something the verified narration does not.
Timing is estimated from a steady speaking rate; an editor retimes against the
recorded voice-over.
"""

from __future__ import annotations

import re

from app.schemas.content_ir import ContentIR, Node

WORDS_PER_SECOND = 2.5
MIN_CUE_SECONDS = 1.5
MAX_LINE_CHARS = 42
MAX_CUE_LINES = 2
SCENE_GAP_SECONDS = 0.5

# Full stop, question/exclamation mark, or a Devanagari danda.
_SENTENCE = re.compile(r"(?<=[.!?।॥])\s*")


def estimate_seconds(text: str) -> float:
    """Spoken duration of a piece of narration at a steady pace."""
    words = len(text.split())
    return max(MIN_CUE_SECONDS, words / WORDS_PER_SECOND) if words else 0.0


def _wrap(sentence: str) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in sentence.split():
        candidate = f"{current} {word}".strip()
        if len(candidate) > MAX_LINE_CHARS and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def cues_for(text: str) -> list[str]:
    """Split narration into subtitle cues of at most two short lines."""
    cues: list[str] = []
    for sentence in _SENTENCE.split(text.strip()):
        lines = _wrap(sentence)
        for i in range(0, len(lines), MAX_CUE_LINES):
            cues.append("\n".join(lines[i : i + MAX_CUE_LINES]))
    return [c for c in cues if c.strip()]


def _timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _narrated(ir: ContentIR) -> list[Node]:
    return [n for n in ir.nodes if n.kind == "scene" and (n.text or "").strip()]


def render(ir: ContentIR, **_: object) -> str:
    out: list[str] = []
    clock = 0.0
    index = 1
    for node in _narrated(ir):
        for cue in cues_for(node.text or ""):
            duration = estimate_seconds(cue.replace("\n", " "))
            out += [
                str(index),
                f"{_timestamp(clock)} --> {_timestamp(clock + duration)}",
                cue,
                "",
            ]
            clock += duration
            index += 1
        clock += SCENE_GAP_SECONDS
    return "\n".join(out)
