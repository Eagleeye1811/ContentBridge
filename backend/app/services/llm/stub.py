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
FACT_MARKER = re.compile(r"^\[(?P<id>f\d+)\]\s*\([^)]*\)\s*(?P<text>.+)$", re.MULTILINE)
ALLOWED_KINDS = re.compile(r"^Allowed node kinds:\s*(?P<kinds>.+)$", re.MULTILINE)
CLAIM_RE = re.compile(r"^CLAIM (?P<n>\d+): (?P<text>.+)$", re.MULTILINE)
EVIDENCE_RE = re.compile(r"^\[e(?P<claim>\d+)\.(?P<k>\d+)\][^\n]*\n(?P<text>.+)$", re.MULTILINE)
MAX_NODES = re.compile(r"^Maximum nodes:\s*(?P<n>\d+)$", re.MULTILINE)
LANGUAGE_RE = re.compile(r"^Write the output in (?P<lang>[^.(]+)", re.MULTILINE)

# Not a translation. A Devanagari marker so the non-English path exercises
# script validation, digit normalization and danda splitting offline.
DEVANAGARI_MARKER = "\u0938\u0942\u091a\u0928\u093e: "
DEVANAGARI_TERMINATOR = "\u0964"
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
        if "verdicts" in fields:
            return schema.model_validate(_verdicts_from_prompt(prompt))
        if "nodes" in fields and "title" in fields:
            return schema.model_validate(_content_ir_from_prompt(prompt))
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


def _content_ir_from_prompt(prompt: str) -> dict:
    """Build a ContentIR that obeys the constraints stated in the prompt.

    Like the fact path, this is not a writing implementation -- it echoes the
    facts it was given so the surrounding machinery (kind validation, citation
    resolution, rendering) is exercised for real.
    """
    kinds_match = ALLOWED_KINDS.search(prompt)
    allowed = (
        [k.strip() for k in kinds_match.group("kinds").split(",") if k.strip()]
        if kinds_match
        else ["heading", "paragraph"]
    )
    max_match = MAX_NODES.search(prompt)
    max_nodes = int(max_match.group("n")) if max_match else 10

    facts = [(m.group("id"), m.group("text").strip()) for m in FACT_MARKER.finditer(prompt)]

    language = LANGUAGE_RE.search(prompt)
    devanagari = bool(language) and language.group("lang").strip().startswith(("Hindi", "Marathi"))

    def localize(statement: str) -> str:
        if not devanagari:
            return statement
        # Numbers stay in Latin digits, exactly as the real prompt instructs.
        return f"{DEVANAGARI_MARKER}{statement.rstrip('.')}{DEVANAGARI_TERMINATOR}"

    nodes: list[dict] = []
    if "heading" in allowed:
        nodes.append(
            {
                "id": "n0",
                "kind": "heading",
                "text": localize("Summary"),
                "level": 2,
                "fact_ids": [],
            }
        )

    # A format's signature kind (scene, panel) wins over generic prose; no
    # format allows both, so existing formats pick exactly what they did before.
    body_kind = next(
        (k for k in ("scene", "panel", "paragraph", "bullets", "post", "slide") if k in allowed),
        None,
    )
    if body_kind is None:
        body_kind = allowed[0] if allowed else "paragraph"

    for i, (label, statement) in enumerate(facts, start=1):
        if len(nodes) >= max_nodes:
            break
        node: dict = {"id": f"n{i}", "kind": body_kind, "fact_ids": [label]}
        localized = localize(statement)
        if body_kind in {"bullets", "post"}:
            node["items"] = [localized]
        elif body_kind == "panel":
            node["title"] = localized[:40]
            node["items"] = [localized]
            node["notes"] = "Single big number with a supporting icon"
        elif body_kind == "scene":
            node["title"] = f"Scene {i}"
            node["text"] = localized
            node["notes"] = "Title card over neutral background footage"
        elif body_kind == "slide":
            node["title"] = localized[:60]
            node["items"] = [localized]
        else:
            node["text"] = localized
        nodes.append(node)

    return {"title": localize("Generated Output"), "nodes": nodes}


def _verdicts_from_prompt(prompt: str) -> dict:
    """Adjudicate by checking whether the claim's figures appear in its evidence.

    Crude on purpose -- it is not a judge. But it is deterministic and it
    exercises the batching, labelling and persistence around the real one.
    """
    evidence: dict[int, list[tuple[str, str]]] = {}
    for m in EVIDENCE_RE.finditer(prompt):
        n = int(m.group("claim"))
        evidence.setdefault(n, []).append((f"e{n}.{m.group('k')}", m.group("text")))

    verdicts = []
    for m in CLAIM_RE.finditer(prompt):
        n = int(m.group("n"))
        claim = m.group("text")
        refs = evidence.get(n, [])
        pool = " ".join(text for _, text in refs)

        numbers = set(re.findall(r"\d[\d,.]*", claim))
        pool_numbers = set(re.findall(r"\d[\d,.]*", pool))

        if not refs:
            verdict, score, why = "unsupported", 0.3, "No evidence was supplied for this claim."
        elif numbers and not numbers <= pool_numbers:
            verdict, score, why = (
                "contradicted",
                0.7,
                "A figure in the claim does not appear in the evidence.",
            )
        elif numbers:
            verdict, score, why = "supported", 0.9, "Every figure appears in the evidence."
        else:
            verdict, score, why = "partial", 0.5, "No figures to check against the evidence."

        verdicts.append(
            {
                "claim_number": n,
                "verdict": verdict,
                "score": score,
                "rationale": why,
                "supporting_labels": [label for label, _ in refs],
            }
        )

    return {"verdicts": verdicts}
