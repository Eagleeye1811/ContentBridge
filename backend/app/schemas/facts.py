from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceOut(BaseModel):
    """A citation resolved all the way to a place in the source."""

    block_id: uuid.UUID
    page_no: int
    section_path: str
    quote: str
    char_start: int | None
    char_end: int | None
    bbox: dict | None


class FactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    type: str
    statement: str
    canonical_value: str | None
    unit: str | None
    confidence: float
    edited_by_human: bool
    evidence: list[EvidenceOut]


class FactSheetOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version: int
    model: str
    created_at: datetime
    facts: list[FactOut]


class FactUpdate(BaseModel):
    """Human correction of the Source of Truth -- the highest-leverage edit."""

    statement: str | None = Field(default=None, min_length=1)
    canonical_value: str | None = None
    unit: str | None = None
    type: str | None = None


class SearchHitOut(BaseModel):
    text: str
    block_ids: list[uuid.UUID]
    page_no: int
    section_path: str
    score: float
