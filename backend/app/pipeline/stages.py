"""The pipeline. Phase 1 implements ingestion; later phases append stages that
consume the same context and the same job-progress plumbing.
"""

from __future__ import annotations

import logging
import uuid

import anyio
from sqlalchemy import delete

from app.db import SessionLocal
from app.models import Document, DocumentBlock, Job
from app.pipeline.jobs import mark
from app.services.ingestion import parse_document
from app.services.storage import storage

log = logging.getLogger(__name__)


async def ingest_document(document_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Parse an uploaded file into traceable blocks.

    Opens its own session: the request that scheduled this has already returned.
    """
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            log.error("ingest: job %s or document %s vanished", job_id, document_id)
            return

        try:
            await mark(db, job, status="running", stage="loading file", progress=0.05)
            document.status = "parsing"
            await db.commit()

            data = await anyio.to_thread.run_sync(storage.get, document.storage_uri)

            await mark(db, job, stage="parsing document", progress=0.2)
            # Parsing is CPU-bound; keep it off the event loop.
            parsed = await anyio.to_thread.run_sync(parse_document, document.filename, data)

            await mark(db, job, stage="storing blocks", progress=0.7)
            # Re-ingest is idempotent: drop any blocks from a previous attempt.
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

            await mark(
                db,
                job,
                status="succeeded",
                stage="done",
                progress=1.0,
                result={"blocks": len(parsed.blocks), "pages": parsed.page_count},
            )
            log.info(
                "ingested %s: %d blocks across %d pages",
                document.filename,
                len(parsed.blocks),
                parsed.page_count,
            )

        except Exception as exc:  # noqa: BLE001 - surfaced to the user via the job row
            log.exception("ingest failed for document %s", document_id)
            await db.rollback()
            document.status = "failed"
            document.error = str(exc)
            await db.commit()
            await mark(db, job, status="failed", stage="failed", error=str(exc))
