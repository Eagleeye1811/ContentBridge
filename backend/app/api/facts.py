from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.models import AuditLog, Document, DocumentBlock, Fact, FactSheet, Job
from app.pipeline.stages import extract_only
from app.schemas.documents import JobOut
from app.schemas.facts import EvidenceOut, FactOut, FactSheetOut, FactUpdate, SearchHitOut
from app.services.llm import llm_available
from app.services.retrieval.search import search as retrieval_search

router = APIRouter(tags=["source of truth"])


async def _owned(db: DbSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    return doc


async def _current_sheet(db: DbSession, document_id: uuid.UUID) -> FactSheet:
    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.document_id == document_id, FactSheet.is_current.is_(True))
        .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
        .order_by(FactSheet.version.desc())
    )
    if sheet is None:
        raise HTTPException(404, "This source has no key facts yet.")
    return sheet


async def _serialize(db: DbSession, sheet: FactSheet) -> FactSheetOut:
    """Resolve every citation to a page, a section and a box."""
    block_ids = {e.block_id for f in sheet.facts for e in f.evidence}
    blocks = {}
    if block_ids:
        rows = await db.scalars(select(DocumentBlock).where(DocumentBlock.id.in_(block_ids)))
        blocks = {b.id: b for b in rows}

    facts_out = []
    for fact in sorted(sheet.facts, key=lambda f: (f.type, f.key)):
        evidence = []
        for e in fact.evidence:
            block = blocks.get(e.block_id)
            if block is None:
                continue
            evidence.append(
                EvidenceOut(
                    block_id=e.block_id,
                    page_no=block.page_no,
                    section_path=block.section_path,
                    quote=e.quote,
                    char_start=e.char_start,
                    char_end=e.char_end,
                    bbox=block.bbox,
                )
            )
        facts_out.append(
            FactOut(
                id=fact.id,
                key=fact.key,
                type=fact.type,
                statement=fact.statement,
                canonical_value=fact.canonical_value,
                unit=fact.unit,
                confidence=fact.confidence,
                edited_by_human=fact.edited_by_human,
                evidence=evidence,
            )
        )

    return FactSheetOut(
        id=sheet.id,
        document_id=sheet.document_id,
        version=sheet.version,
        model=sheet.model,
        created_at=sheet.created_at,
        facts=facts_out,
    )


@router.get("/documents/{document_id}/fact-sheet", response_model=FactSheetOut)
async def get_fact_sheet(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> FactSheetOut:
    await _owned(db, user, document_id)
    return await _serialize(db, await _current_sheet(db, document_id))


@router.post("/documents/{document_id}/fact-sheet", response_model=JobOut, status_code=202)
async def run_extraction(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> JobOut:
    """(Re)extract the Source of Truth. Produces a new version each time."""
    doc = await _owned(db, user, document_id)
    if doc.status in {"uploaded", "parsing", "failed"}:
        raise HTTPException(409, f"Document is not ready for extraction (status: {doc.status})")
    if not llm_available():
        raise HTTPException(
            503,
            "No LLM provider configured. Set GEMINI_API_KEY, or LLM_PROVIDER=stub for an "
            "offline dry run.",
        )

    job = Job(document_id=document_id, kind="extract", status="queued", stage="queued")
    db.add(job)
    db.add(AuditLog(actor_id=user.id, entity="document", entity_id=document_id, action="extract"))
    # Commit before scheduling: the task opens its own session.
    await db.commit()

    background.add_task(extract_only, document_id, job.id)
    return JobOut.model_validate(job)


@router.patch("/facts/{fact_id}", response_model=FactOut)
async def update_fact(
    fact_id: uuid.UUID, body: FactUpdate, db: DbSession, user: CurrentUser
) -> FactOut:
    """Correcting a fact corrects every output generated from it afterwards."""
    fact = await db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(404, "Fact not found")

    sheet = await db.get(FactSheet, fact.fact_sheet_id)
    if sheet is None:
        raise HTTPException(404, "Fact not found")
    await _owned(db, user, sheet.document_id)

    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No fields to update")
    for field, value in changes.items():
        setattr(fact, field, value)
    fact.edited_by_human = True

    db.add(
        AuditLog(actor_id=user.id, entity="fact", entity_id=fact.id, action="edit", payload=changes)
    )
    await db.commit()

    refreshed = await db.scalar(
        select(FactSheet)
        .where(FactSheet.id == sheet.id)
        .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
    )
    serialized = await _serialize(db, refreshed)
    return next(f for f in serialized.facts if f.id == fact_id)


@router.get("/documents/{document_id}/search", response_model=list[SearchHitOut])
async def search_document(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    q: str = Query(min_length=2, description="Natural-language query"),
    limit: int = Query(8, ge=1, le=25),
) -> list[SearchHitOut]:
    """Retrieval with provenance -- also the quickest way to prove RAG works."""
    await _owned(db, user, document_id)
    hits = await retrieval_search(document_id, q, limit=limit)
    return [
        SearchHitOut(
            text=h.text,
            block_ids=h.block_ids,
            page_no=h.page_no,
            section_path=h.section_path,
            score=h.score,
        )
        for h in hits
    ]
