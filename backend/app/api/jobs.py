from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.deps import CurrentUser, DbSession
from app.db import SessionLocal
from app.models import Document, Job
from app.pipeline.jobs import TERMINAL
from app.schemas.documents import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

POLL_SECONDS = 0.4
MAX_STREAM_SECONDS = 600


async def _owned_job(db: DbSession, user: CurrentUser, job_id: uuid.UUID) -> Job:
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    document = await db.get(Document, job.document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser) -> JobOut:
    return JobOut.model_validate(await _owned_job(db, user, job_id))


@router.get("/{job_id}/stream")
async def stream_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser) -> EventSourceResponse:
    """Server-sent progress. Emits on every change and closes when terminal."""
    await _owned_job(db, user, job_id)  # authorize once, up front

    async def events():
        last: str | None = None
        waited = 0.0
        while waited < MAX_STREAM_SECONDS:
            # A fresh session each tick: the pipeline commits from another one.
            async with SessionLocal() as poll_db:
                job = await poll_db.get(Job, job_id)
                if job is None:
                    yield {"event": "error", "data": '{"detail":"Job disappeared"}'}
                    return
                payload = JobOut.model_validate(job).model_dump_json()
                status = job.status

            if payload != last:
                yield {"event": "progress", "data": payload}
                last = payload

            if status in TERMINAL:
                yield {"event": "done", "data": payload}
                return

            await asyncio.sleep(POLL_SECONDS)
            waited += POLL_SECONDS

        yield {"event": "error", "data": '{"detail":"Stream timed out"}'}

    return EventSourceResponse(events())
