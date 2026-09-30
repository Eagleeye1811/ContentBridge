from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    page_no: int
    section_path: str
    order_idx: int
    block_type: str
    text: str
    bbox: dict | None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    mime: str
    size_bytes: int
    page_count: int
    source_lang: str
    status: str
    error: str | None
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    kind: str
    status: str
    stage: str
    progress: float
    result: dict | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None


class UploadResponse(BaseModel):
    document: DocumentOut
    job: JobOut
