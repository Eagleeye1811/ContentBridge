"""Job bookkeeping. Progress is written to the DB so SSE can stream it."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job

TERMINAL = {"succeeded", "failed"}


async def mark(
    db: AsyncSession,
    job: Job,
    *,
    stage: str | None = None,
    progress: float | None = None,
    status: str | None = None,
    error: str | None = None,
    result: dict | None = None,
) -> None:
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = round(progress, 3)
    if status is not None:
        job.status = status
        if status in TERMINAL:
            job.finished_at = datetime.now(UTC)
    if error is not None:
        job.error = error
    if result is not None:
        job.result = result
    # Commit immediately: the SSE stream reads these rows from another session.
    await db.commit()
