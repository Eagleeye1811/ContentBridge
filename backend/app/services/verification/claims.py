"""Layer 2: adjudicating claims against the source.

Where Layer 1 compares canonical values, this asks whether the prose is
actually supported by the blocks it cites. Evidence is the blocks behind the
cited facts, plus a retrieval fallback so an uncited claim still gets a fair
hearing rather than an automatic failure.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from app.services.llm import get_llm
from app.services.verification.atomizer import Claim

log = logging.getLogger(__name__)

BATCH_SIZE = 6
MAX_EVIDENCE_PER_CLAIM = 5
Verdict = Literal["supported", "partial", "unsupported", "contradicted"]

SYSTEM = """You adjudicate whether a claim is supported by the source evidence quoted for it.

Verdicts:
- supported: the evidence states the claim, including every figure in it.
- partial: the evidence supports part of the claim but not all of it, or
  supports it less specifically than the claim asserts.
- unsupported: the evidence neither states nor denies the claim.
- contradicted: the evidence states something incompatible with the claim.

Rules:
- Judge ONLY against the evidence shown. Outside knowledge is irrelevant.
- A claim whose numbers disagree with the evidence is `contradicted`, never
  `partial`.
- Cite the evidence labels that decided your verdict.
- `score` is your confidence in the verdict, from 0 to 1.
"""


class ClaimVerdict(BaseModel):
    claim_number: int = Field(description="the CLAIM number this verdict is for")
    verdict: Verdict
    score: float = Field(default=0.8, ge=0.0, le=1.0)
    rationale: str = Field(description="one sentence, referencing the evidence")
    supporting_labels: list[str] = Field(
        default_factory=list, description="evidence labels used, e.g. ['e1.0']"
    )


class VerificationBatch(BaseModel):
    verdicts: list[ClaimVerdict]


@dataclass(slots=True)
class EvidenceRef:
    block_id: uuid.UUID
    text: str
    page_no: int
    section_path: str
    similarity: float | None = None


@dataclass(slots=True)
class ClaimResult:
    claim: Claim
    verdict: Verdict
    score: float
    rationale: str
    evidence: list[EvidenceRef] = field(default_factory=list)


def evidence_fingerprint(claim_text: str, evidence: Sequence[EvidenceRef]) -> str:
    """Stable key for reuse: re-verifying an unchanged claim is free."""
    ids = ",".join(sorted(str(e.block_id) for e in evidence))
    return hashlib.sha256(f"{claim_text}\u0000{ids}".encode()).hexdigest()


def _render_batch(
    batch: Sequence[tuple[Claim, list[EvidenceRef]]],
) -> tuple[str, dict[str, EvidenceRef]]:
    labels: dict[str, EvidenceRef] = {}
    parts: list[str] = []
    for i, (claim, evidence) in enumerate(batch, start=1):
        parts.append(f"CLAIM {i}: {claim.text}")
        if not evidence:
            parts.append("EVIDENCE: (none found)")
        else:
            parts.append(f"EVIDENCE FOR CLAIM {i}:")
            for k, ref in enumerate(evidence):
                label = f"e{i}.{k}"
                labels[label] = ref
                parts.append(f'[{label}] (page {ref.page_no}, section "{ref.section_path}")')
                parts.append(ref.text)
        parts.append("")
    return "\n".join(parts), labels


async def gather_evidence(
    claims: Sequence[Claim],
    evidence_for: Callable[[Claim], Awaitable[list[EvidenceRef]]],
) -> list[tuple[Claim, list[EvidenceRef]]]:
    prepared = []
    for claim in claims:
        evidence = (await evidence_for(claim))[:MAX_EVIDENCE_PER_CLAIM]
        prepared.append((claim, evidence))
    return prepared


async def verify_claims(
    claims: Sequence[Claim],
    evidence_for: Callable[[Claim], Awaitable[list[EvidenceRef]]],
) -> list[ClaimResult]:
    return await verify_prepared(await gather_evidence(claims, evidence_for))


async def verify_prepared(
    prepared: Sequence[tuple[Claim, list[EvidenceRef]]],
) -> list[ClaimResult]:
    """Adjudicate claims that already have their evidence. Batched to keep
    call volume sane."""
    if not prepared:
        return []

    llm = get_llm()
    results: list[ClaimResult] = []

    for start in range(0, len(prepared), BATCH_SIZE):
        batch = prepared[start : start + BATCH_SIZE]
        prompt, labels = _render_batch(batch)

        try:
            response = await llm.complete_structured(
                system=SYSTEM,
                prompt=f"Adjudicate each claim.\n\n{prompt}",
                schema=VerificationBatch,
            )
            by_number = {v.claim_number: v for v in response.verdicts}
        except Exception as exc:  # noqa: BLE001 - a failed batch must not lose the rest
            log.exception("claim verification batch failed")
            by_number = {}
            log.warning("treating batch as unverified: %s", exc)

        for i, (claim, evidence) in enumerate(batch, start=1):
            verdict = by_number.get(i)
            if verdict is None:
                results.append(
                    ClaimResult(
                        claim=claim,
                        verdict="unsupported",
                        score=0.0,
                        rationale="The model returned no verdict for this claim.",
                        evidence=evidence,
                    )
                )
                continue

            used = [labels[label] for label in verdict.supporting_labels if label in labels]
            results.append(
                ClaimResult(
                    claim=claim,
                    verdict=verdict.verdict,
                    score=verdict.score,
                    rationale=verdict.rationale,
                    evidence=used or evidence,
                )
            )

    return results
