"""The one pipeline.

Intake runs parse -> index -> extract as a single job so the UI shows one
progress bar with honest stage names. Each stage is an independent coroutine,
so moving to a real worker queue later is mechanical.
"""

from __future__ import annotations

import logging
import uuid

import anyio
from sqlalchemy import delete, select, update

from app.db import SessionLocal
from app.models import Chunk, Document, DocumentBlock, Fact, FactEvidence, FactSheet, Job
from app.pipeline.jobs import mark
from app.services.indexing.chunker import chunk_blocks
from app.services.indexing.embeddings import get_embedder
from app.services.indexing.qdrant_store import ChunkPoint, VectorStore
from app.services.ingestion import parse_document
from app.services.llm import llm_available
from app.services.sot.fact_extractor import extract_facts
from app.services.storage import storage

log = logging.getLogger(__name__)

# Progress is split across the three stages so the bar moves sensibly.
PARSE_SPAN = (0.05, 0.30)
INDEX_SPAN = (0.30, 0.60)
EXTRACT_SPAN = (0.60, 1.00)


def _lerp(span: tuple[float, float], fraction: float) -> float:
    lo, hi = span
    return lo + (hi - lo) * max(0.0, min(1.0, fraction))


# --------------------------------------------------------------------------
# Stage 1: parse
# --------------------------------------------------------------------------


async def _parse(db, document: Document, job: Job) -> int:
    await mark(db, job, stage="parsing document", progress=PARSE_SPAN[0])
    document.status = "parsing"
    await db.commit()

    data = await anyio.to_thread.run_sync(storage.get, document.storage_uri)
    parsed = await anyio.to_thread.run_sync(parse_document, document.filename, data)

    # Re-ingest is idempotent: drop anything from a previous attempt.
    await db.execute(delete(DocumentBlock).where(DocumentBlock.document_id == document.id))
    db.add_all(
        DocumentBlock(
            document_id=document.id,
            page_no=b.page_no,
            section_path=b.section_path,
            order_idx=b.order_idx,
            block_type=b.block_type,
            text=b.text,
            bbox=b.bbox,
        )
        for b in parsed.blocks
    )
    document.page_count = parsed.page_count
    document.status = "parsed"
    document.error = None
    await db.commit()
    return len(parsed.blocks)


# --------------------------------------------------------------------------
# Stage 2: index
# --------------------------------------------------------------------------


async def _index(db, document: Document, job: Job) -> int:
    await mark(db, job, stage="indexing chunks", progress=INDEX_SPAN[0])
    document.status = "indexing"
    await db.commit()

    blocks = list(
        await db.scalars(
            select(DocumentBlock)
            .where(DocumentBlock.document_id == document.id)
            .order_by(DocumentBlock.order_idx)
        )
    )
    chunks = chunk_blocks(blocks)
    if not chunks:
        document.status = "indexed"
        await db.commit()
        return 0

    embedder = get_embedder()
    store = VectorStore()
    try:
        await store.ensure_collection(embedder.dim)
        # Replace rather than append, so re-indexing cannot leave stale vectors.
        await store.delete_document(document.id)
        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))

        vectors = await embedder.embed([c.text for c in chunks])
        await mark(db, job, progress=_lerp(INDEX_SPAN, 0.7))

        points, rows = [], []
        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = str(uuid.uuid4())
            points.append(
                ChunkPoint(
                    point_id=point_id,
                    vector=vector,
                    document_id=document.id,
                    block_ids=chunk.block_ids,
                    text=chunk.text,
                    page_no=chunk.page_no,
                    section_path=chunk.section_path,
                )
            )
            rows.append(
                Chunk(
                    document_id=document.id,
                    block_ids=chunk.block_ids,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    qdrant_point_id=point_id,
                )
            )

        await store.upsert(points)
        db.add_all(rows)
        document.status = "indexed"
        await db.commit()
    finally:
        await store.close()

    return len(chunks)


# --------------------------------------------------------------------------
# Stage 3: extract the Source of Truth
# --------------------------------------------------------------------------


async def _extract(db, document: Document, job: Job) -> int:
    from app.config import settings

    await mark(db, job, stage="extracting facts", progress=EXTRACT_SPAN[0])
    document.status = "extracting"
    await db.commit()

    blocks = list(
        await db.scalars(
            select(DocumentBlock)
            .where(DocumentBlock.document_id == document.id)
            .order_by(DocumentBlock.order_idx)
        )
    )

    facts = await extract_facts(blocks)

    # Supersede any previous sheet rather than deleting it: approvals and
    # outputs reference the version they were generated from.
    previous = await db.scalar(
        select(FactSheet)
        .where(FactSheet.document_id == document.id)
        .order_by(FactSheet.version.desc())
    )
    await db.execute(
        update(FactSheet).where(FactSheet.document_id == document.id).values(is_current=False)
    )

    sheet = FactSheet(
        document_id=document.id,
        version=(previous.version + 1) if previous else 1,
        model=settings.llm_model if settings.llm_provider != "stub" else "stub",
        is_current=True,
    )
    db.add(sheet)
    await db.flush()

    for fact in facts:
        row = Fact(
            fact_sheet_id=sheet.id,
            key=fact.key,
            type=fact.type,
            statement=fact.statement,
            canonical_value=fact.canonical_value,
            unit=fact.unit,
            confidence=fact.confidence,
        )
        db.add(row)
        await db.flush()
        db.add_all(
            FactEvidence(
                fact_id=row.id,
                block_id=e.block_id,
                quote=e.quote,
                char_start=e.char_start,
                char_end=e.char_end,
            )
            for e in fact.evidence
        )

    document.status = "ready"
    await db.commit()
    return len(facts)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


async def process_document(document_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Full intake. Opens its own session: the request has already returned."""
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            log.error("intake: job %s or document %s vanished", job_id, document_id)
            return

        try:
            await mark(db, job, status="running", stage="starting", progress=0.02)

            block_count = await _parse(db, document, job)
            chunk_count = await _index(db, document, job)

            result = {"blocks": block_count, "chunks": chunk_count, "pages": document.page_count}

            if llm_available():
                result["facts"] = await _extract(db, document, job)
                note = None
            else:
                # Degrade gracefully: the document is still fully searchable and
                # every block is citable. Extraction can be triggered later.
                note = (
                    "No LLM configured - skipped fact extraction. Set GEMINI_API_KEY "
                    "(or LLM_PROVIDER=stub), then POST /documents/{id}/fact-sheet."
                )
                result["facts"] = 0
                result["note"] = note
                log.warning("intake: %s", note)

            await mark(db, job, status="succeeded", stage="done", progress=1.0, result=result)
            log.info("intake complete for %s: %s", document.filename, result)

        except Exception as exc:  # noqa: BLE001 - surfaced through the job row
            log.exception("intake failed for document %s", document_id)
            await db.rollback()
            document.status = "failed"
            document.error = str(exc)
            await db.commit()
            await mark(db, job, status="failed", stage="failed", error=str(exc))


async def extract_only(document_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Re-run extraction against an already-indexed document."""
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            return
        try:
            await mark(db, job, status="running", stage="extracting facts", progress=0.1)
            count = await _extract(db, document, job)
            await mark(
                db, job, status="succeeded", stage="done", progress=1.0, result={"facts": count}
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("extraction failed for document %s", document_id)
            await db.rollback()
            await mark(db, job, status="failed", stage="failed", error=str(exc))
