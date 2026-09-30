"""A deterministic provider for tests and offline demos.

It is NOT an extraction implementation: it reads the block markers out of the
prompt it was given and echoes back the sentences that contain numbers, citing
the blocks they came from. That is enough to exercise the real code path --
schema validation, evidence resolution, normalization, deduplication -- with
no network and no API key.
"""

from __future__ import annotations

import re

from app.services.llm.base import LLMError, T

BLOCK_MARKER = re.compile(r"^\[(?P<id>b\d+)\]", re.MULTILINE)
NUMERIC = re.compile(r"\d")
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def _blocks_from_prompt(prompt: str) -> list[tuple[str, str]]:
    """Recover (block_id, text) pairs from a prompt built by the extractor."""
    out: list[tuple[str, str]] = []
    matches = list(BLOCK_MARKER.finditer(prompt))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt)
        body = prompt[m.end() : end]
        # Drop the "(page N, section ...)" header line the extractor writes.
        lines = [ln for ln in body.splitlines() if ln.strip()]
        if lines and lines[0].lstrip().startswith("("):
            lines = lines[1:]
        text = " ".join(ln.strip() for ln in lines).strip()
        if text:
            out.append((m.group("id"), text))
    return out


class StubProvider:
    name = "stub"

    async def complete_structured(
        self, *, system: str, prompt: str, schema: type[T], temperature: float | None = None
    ) -> T:
        fields = schema.model_fields
        if "facts" not in fields:
            raise LLMError(f"StubProvider does not know how to fill {schema.__name__}")

        facts = []
        for block_id, text in _blocks_from_prompt(prompt):
            for sentence in SENTENCE.split(text):
                sentence = sentence.strip()
                if len(sentence) < 20 or not NUMERIC.search(sentence):
                    continue
                number = re.search(r"\d[\d,.]*", sentence)
                facts.append(
                    {
                        "key": re.sub(r"[^a-z0-9]+", "_", sentence.lower())[:60].strip("_"),
                        "type": "metric",
                        "statement": sentence,
                        "value": number.group(0) if number else None,
                        "unit": None,
                        "evidence_block_ids": [block_id],
                        "confidence": 0.5,
                    }
                )
                break  # one fact per block keeps stub output small and stable

        return schema.model_validate({"facts": facts})
