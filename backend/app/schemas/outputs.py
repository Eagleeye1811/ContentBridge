from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content_ir import ContentIR
from app.schemas.facts import FactOut


class GenerateRequest(BaseModel):
    """One request fans out to types x languages, all through one generator."""

    types: list[str] = Field(min_length=1, description="e.g. ['advisory','summary']")
    audience: str = "officer"
    languages: list[str] = Field(default=["en"], min_length=1)


class OutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    fact_sheet_id: uuid.UUID
    type: str
    audience: str
    language: str
    status: str
    trust_score: float | None
    version: int
    model: str
    created_at: datetime
    title: str = ""
    renderers: list[str] = Field(default_factory=list)


class OutputDetail(OutputOut):
    content_ir: ContentIR
    # Every fact cited anywhere in this output, so citation chips resolve
    # without a second round trip.
    facts: list[FactOut]


class ContentIRUpdate(BaseModel):
    content_ir: ContentIR


class FormatInfo(BaseModel):
    key: str
    name: str
    description: str
    renderers: list[str]


class AudienceInfo(BaseModel):
    key: str
    name: str


class CatalogOut(BaseModel):
    """What the Studio page offers. Driven by the registries, never hardcoded."""

    formats: list[FormatInfo]
    audiences: list[AudienceInfo]
    languages: dict[str, str]
