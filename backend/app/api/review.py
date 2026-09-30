"""Human review: submit, approve, reject, and the record of who did what.

The gate is the point of the phase. An output with a contradicted claim or an
unresolved high-severity mismatch cannot be approved, and the reason is stated
rather than implied.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, require_role
from app.models import (
    AuditLog,
    ConsistencyIssue,
    Document,
    Output,
    OutputClaim,
    Review,
    User,
)
from app.schemas.review import (
    ApprovalState,
    AuditEntry,
    PendingOutput,
    RejectAction,
    ReviewAction,
    ReviewOut,
)
from app.services.review.policy import can_view, permissions
from app.services.verification.scoring import blocking_reasons

router = APIRouter(tags=["review"])

Approver = Annotated[User, Depends(require_role("approver"))]


async def _visible_output(db: DbSession, user: User, output_id: uuid.UUID) -> Output:
    """Owners see their own work; approvers see anything submitted for review.

    Without this an approver could never act on an editor's output, which is
    the whole point of having two roles.
    """
    output = await db.get(Output, output_id)
    if output is None:
        raise HTTPException(404, "Output not found")

    document = await db.get(Document, output.document_id)
    if document is None:
        raise HTTPException(404, "Output not found")

    if not can_view(status=output.status, role=user.role, is_owner=document.owner_id == user.id):
        raise HTTPException(404, "Output not found")
    return output


async def _blockers(db: DbSession, output: Output) -> list[str]:
    """Why this output cannot be approved yet. Empty means it can."""
    if output.verified_at is None:
        # An unverified output has no claims, so the verdict-based check would
        # vacuously pass. Say so explicitly instead.
        return ["not verified yet"]

    claims = list(await db.scalars(select(OutputClaim).where(OutputClaim.output_id == output.id)))
    issues = list(
        await db.scalars(
            select(ConsistencyIssue).where(
                ConsistencyIssue.document_id == output.document_id,
                ConsistencyIssue.status == "open",
                ConsistencyIssue.severity == "high",
            )
        )
    )
    mine = sum(1 for i in issues if str(output.id) in (i.observed or {}))
    return blocking_reasons([c.verdict or "" for c in claims], mine)


async def _history(db: DbSession, output_id: uuid.UUID) -> list[ReviewOut]:
    rows = list(
        await db.scalars(
            select(Review).where(Review.output_id == output_id).order_by(Review.created_at)
        )
    )
    actors = {}
    ids = {r.user_id for r in rows if r.user_id}
    if ids:
        actors = {u.id: u for u in await db.scalars(select(User).where(User.id.in_(ids)))}
    return [
        ReviewOut.model_validate(r).model_copy(
            update={
                "actor_name": actors[r.user_id].name if r.user_id in actors else "",
                "actor_role": actors[r.user_id].role if r.user_id in actors else "",
            }
        )
        for r in rows
    ]


async def _state(db: DbSession, output: Output, user: User) -> ApprovalState:
    reasons = await _blockers(db, output)
    approver = await db.get(User, output.approved_by) if output.approved_by else None
    document = await db.get(Document, output.document_id)
    is_owner = document is not None and document.owner_id == user.id

    allowed = permissions(
        status=output.status,
        role=user.role,
        is_owner=is_owner,
        verified=output.verified_at is not None,
        blocked=bool(reasons),
    )

    return ApprovalState(
        output_id=output.id,
        status=output.status,
        trust_score=output.trust_score,
        verified_at=output.verified_at,
        approved_by=output.approved_by,
        approved_at=output.approved_at,
        approver_name=approver.name if approver else None,
        blocking_reasons=reasons,
        can_submit=allowed.can_submit,
        can_approve=allowed.can_approve,
        can_reject=allowed.can_reject,
        history=await _history(db, output.id),
    )


@router.get("/outputs/{output_id}/approval", response_model=ApprovalState)
async def approval_state(output_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ApprovalState:
    return await _state(db, await _visible_output(db, user, output_id), user)


@router.post("/outputs/{output_id}/submit", response_model=ApprovalState)
async def submit_for_review(
    output_id: uuid.UUID, body: ReviewAction, db: DbSession, user: CurrentUser
) -> ApprovalState:
    output = await _visible_output(db, user, output_id)
    if output.status == "approved":
        raise HTTPException(409, "Already approved.")
    if output.verified_at is None:
        raise HTTPException(409, "Verify the output before submitting it for review.")

    output.status = "in_review"
    db.add(Review(output_id=output.id, user_id=user.id, action="comment", note=body.note))
    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="submit"))
    await db.commit()
    return await _state(db, output, user)


@router.post("/outputs/{output_id}/approve", response_model=ApprovalState)
async def approve(
    output_id: uuid.UUID, body: ReviewAction, db: DbSession, user: Approver
) -> ApprovalState:
    output = await _visible_output(db, user, output_id)
    if output.status == "approved":
        raise HTTPException(409, "Already approved.")
    if output.status != "in_review":
        raise HTTPException(409, "Only an output submitted for review can be approved.")

    reasons = await _blockers(db, output)
    if reasons:
        # The gate. Refuse, and say exactly why.
        raise HTTPException(409, f"Cannot approve: {'; '.join(reasons)}")

    output.status = "approved"
    output.approved_by = user.id
    output.approved_at = datetime.now(UTC)
    db.add(Review(output_id=output.id, user_id=user.id, action="approve", note=body.note))
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="output",
            entity_id=output.id,
            action="approve",
            payload={"trust_score": output.trust_score},
        )
    )
    await db.commit()
    return await _state(db, output, user)


@router.post("/outputs/{output_id}/reject", response_model=ApprovalState)
async def reject(
    output_id: uuid.UUID, body: RejectAction, db: DbSession, user: Approver
) -> ApprovalState:
    output = await _visible_output(db, user, output_id)
    if output.status != "in_review":
        raise HTTPException(409, "Only an output submitted for review can be rejected.")

    output.status = "rejected"
    db.add(Review(output_id=output.id, user_id=user.id, action="reject", note=body.note))
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="output",
            entity_id=output.id,
            action="reject",
            payload={"note": body.note},
        )
    )
    await db.commit()
    return await _state(db, output, user)


@router.get("/outputs/{output_id}/reviews", response_model=list[ReviewOut])
async def list_reviews(output_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[ReviewOut]:
    await _visible_output(db, user, output_id)
    return await _history(db, output_id)


@router.get("/review-queue", response_model=list[PendingOutput])
async def review_queue(db: DbSession, user: CurrentUser) -> list[PendingOutput]:
    """Outputs awaiting a decision. Approvers see everything submitted."""
    stmt = select(Output, Document).join(Document, Document.id == Output.document_id)
    if user.role == "approver":
        stmt = stmt.where(Output.status == "in_review")
    else:
        stmt = stmt.where(
            Document.owner_id == user.id, Output.status.in_(["in_review", "rejected"])
        )

    rows = (await db.execute(stmt.order_by(Output.created_at.desc()))).all()
    return [
        PendingOutput(
            id=o.id,
            document_id=d.id,
            document_name=d.filename,
            type=o.type,
            audience=o.audience,
            language=o.language,
            version=o.version,
            status=o.status,
            trust_score=o.trust_score,
            title=(o.content_ir or {}).get("title", ""),
            submitted_at=o.created_at,
        )
        for o, d in rows
    ]


@router.get("/documents/{document_id}/audit", response_model=list[AuditEntry])
async def document_audit(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> list[AuditEntry]:
    """Who did what to this document and everything generated from it."""
    document = await db.get(Document, document_id)
    if document is None or (document.owner_id != user.id and user.role != "approver"):
        raise HTTPException(404, "Document not found")

    output_ids = list(await db.scalars(select(Output.id).where(Output.document_id == document_id)))
    entity_ids = [document_id, *output_ids]

    rows = list(
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.entity_id.in_(entity_ids))
            .order_by(AuditLog.created_at.desc())
            .limit(200)
        )
    )
    actors = {}
    ids = {r.actor_id for r in rows if r.actor_id}
    if ids:
        actors = {u.id: u for u in await db.scalars(select(User).where(User.id.in_(ids)))}

    return [
        AuditEntry.model_validate(r).model_copy(
            update={"actor_name": actors[r.actor_id].name if r.actor_id in actors else ""}
        )
        for r in rows
    ]
