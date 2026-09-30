from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import (
    AuditLog,
    ClaimEvidence,
    ConsistencyIssue,
    Document,
    DocumentBlock,
    Fact,
    FactSheet,
    Job,
    Output,
    OutputClaim,
)
from app.pipeline.stages import verify_output
from app.schemas.content_ir import ContentIR
from app.schemas.documents import JobOut
from app.schemas.verification import (
    ClaimEvidenceOut,
    ClaimOut,
    ConsistencyReport,
    IssueOut,
    IssueUpdate,
    MatrixCell,
    MatrixRowOut,
    OutputColumn,
    UnsourcedOut,
    VerificationSummary,
)
from app.services.llm import llm_available
from app.services.verification.consistency import analyze
from app.services.verification.scoring import blocking_reasons

router = APIRouter(tags=["verification"])


async def _owned_document(db: DbSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    return doc


async def _owned_output(db: DbSession, user: CurrentUser, output_id: uuid.UUID) -> Output:
    output = await db.get(Output, output_id)
    if output is None:
        raise HTTPException(404, "Output not found")
    await _owned_document(db, user, output.document_id)
    return output


@router.post("/outputs/{output_id}/verify", response_model=JobOut, status_code=202)
async def start_verification(
    output_id: uuid.UUID, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> JobOut:
    output = await _owned_output(db, user, output_id)
    if not llm_available():
        raise HTTPException(
            503,
            "Claim verification needs an LLM. The consistency matrix at "
            "/documents/{id}/consistency works without one.",
        )

    job = Job(document_id=output.document_id, kind="verify", status="queued", stage="queued")
    db.add(job)
    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="verify"))
    # Commit before scheduling: the task opens its own session.
    await db.commit()

    background.add_task(verify_output, output_id, job.id)
    return JobOut.model_validate(job)


@router.get("/outputs/{output_id}/claims", response_model=VerificationSummary)
async def get_claims(output_id: uuid.UUID, db: DbSession, user: CurrentUser) -> VerificationSummary:
    output = await _owned_output(db, user, output_id)

    claims = list(
        await db.scalars(
            select(OutputClaim)
            .where(OutputClaim.output_id == output_id)
            .order_by(OutputClaim.node_id)
        )
    )
    blocks = {
        b.id: b
        for b in await db.scalars(
            select(DocumentBlock).where(DocumentBlock.document_id == output.document_id)
        )
    }

    out: list[ClaimOut] = []
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim.verdict or "unverified"] = counts.get(claim.verdict or "unverified", 0) + 1
        links = await db.scalars(select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id))
        evidence = []
        for link in links:
            block = blocks.get(link.block_id)
            if block is None:
                continue
            evidence.append(
                ClaimEvidenceOut(
                    block_id=block.id,
                    page_no=block.page_no,
                    section_path=block.section_path,
                    quote=block.text[:600],
                    similarity=link.similarity,
                )
            )
        out.append(ClaimOut.model_validate(claim).model_copy(update={"evidence": evidence}))

    open_high = await db.scalar(
        select(ConsistencyIssue).where(
            ConsistencyIssue.document_id == output.document_id,
            ConsistencyIssue.status == "open",
            ConsistencyIssue.severity == "high",
        )
    )
    open_high_count = 0
    if open_high is not None:
        rows = await db.scalars(
            select(ConsistencyIssue).where(
                ConsistencyIssue.document_id == output.document_id,
                ConsistencyIssue.status == "open",
                ConsistencyIssue.severity == "high",
            )
        )
        open_high_count = sum(1 for r in rows if str(output.id) in (r.observed or {}))

    return VerificationSummary(
        output_id=output.id,
        status=output.status,
        trust_score=output.trust_score,
        verified_at=output.verified_at,
        counts=counts,
        blocking_reasons=blocking_reasons([c.verdict or "" for c in claims], open_high_count),
        claims=out,
    )


@router.get("/documents/{document_id}/consistency", response_model=ConsistencyReport)
async def consistency(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> ConsistencyReport:
    """The facts x outputs matrix. Pure computation -- no LLM, always instant."""
    await _owned_document(db, user, document_id)

    outputs = list(
        await db.scalars(
            select(Output).where(Output.document_id == document_id).order_by(Output.type)
        )
    )
    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.document_id == document_id, FactSheet.is_current.is_(True))
        .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
    )
    if sheet is None:
        raise HTTPException(409, "No Source of Truth yet. Run extraction first.")

    result = analyze(
        list(sheet.facts),
        [(str(o.id), ContentIR.model_validate(o.content_ir)) for o in outputs],
    )
    issues = list(
        await db.scalars(
            select(ConsistencyIssue)
            .where(ConsistencyIssue.document_id == document_id)
            .order_by(ConsistencyIssue.severity, ConsistencyIssue.created_at)
        )
    )

    return ConsistencyReport(
        document_id=document_id,
        outputs=[
            OutputColumn(
                id=o.id,
                type=o.type,
                audience=o.audience,
                language=o.language,
                version=o.version,
                trust_score=o.trust_score,
            )
            for o in outputs
        ],
        rows=[
            MatrixRowOut(
                fact_id=uuid.UUID(r.fact_id),
                key=r.key,
                statement=r.statement,
                expected=r.expected,
                unit=r.unit,
                has_mismatch=r.has_mismatch,
                cells=[
                    MatrixCell(
                        output_id=uuid.UUID(c.output_id),
                        stated=c.stated,
                        agrees=c.agrees,
                        snippet=c.snippet,
                    )
                    for c in r.cells
                ],
            )
            for r in result.rows
        ],
        unsourced=[
            UnsourcedOut(output_id=uuid.UUID(u.output_id), value=u.value, snippet=u.snippet)
            for u in result.unsourced
        ],
        issues=[IssueOut.model_validate(i) for i in issues],
    )


@router.patch("/consistency-issues/{issue_id}", response_model=IssueOut)
async def update_issue(
    issue_id: uuid.UUID, body: IssueUpdate, db: DbSession, user: CurrentUser
) -> IssueOut:
    """Resolve or accept a flagged mismatch. The system never silently rewrites."""
    issue = await db.get(ConsistencyIssue, issue_id)
    if issue is None:
        raise HTTPException(404, "Issue not found")
    await _owned_document(db, user, issue.document_id)

    issue.status = body.status
    if body.note is not None:
        issue.note = body.note
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="consistency_issue",
            entity_id=issue.id,
            action=body.status,
            payload={"note": body.note},
        )
    )
    await db.commit()
    return IssueOut.model_validate(issue)
