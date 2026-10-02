from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content_ir import ContentIR
from app.schemas.facts import FactOut


class GenerateRequest(BaseModel):
    """One request fans out to types x languages, all through one generator."""

    types: list[str] = Field(min_length=1, description="e.g. ['advisory','summary']")
    languages: list[str] = Field(default=["en"], min_length=1)
    # Format-specific options, keyed by output type, e.g.
    # {"ppt": {"slides": "5"}}. Declared by each FormatSpec.
    options: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Optional overrides. Left out, each output type uses the audience and
    # writing controls that suit it (FormatSpec.defaults), and an option such
    # as "Presenting to" can set the audience.
    audience: str | None = None
    tone: str | None = None
    detail_level: str | None = None
    objective: str | None = None
    style: str | None = None

    def controls(self) -> dict[str, str]:
        values = {
            "tone": self.tone,
            "detail_level": self.detail_level,
            "objective": self.objective,
            "style": self.style,
        }
        return {k: v for k, v in values.items() if v}


class OutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    fact_sheet_id: uuid.UUID
    type: str
    audience: str
    language: str
    # Communication controls, plus the format options under "format".
    controls: dict[str, Any] = Field(default_factory=dict)
    status: str
    trust_score: float | None
    version: int
    model: str
    created_at: datetime
    title: str = ""
    renderers: list[str] = Field(default_factory=list)


class OutputListItem(OutputOut):
    """An output in the cross-source list, with the source it came from."""

    document_name: str = ""


class OutputDetail(OutputOut):
    content_ir: ContentIR
    # Every fact cited anywhere in this output, so citation chips resolve
    # without a second round trip.
    facts: list[FactOut]


class ContentIRUpdate(BaseModel):
    content_ir: ContentIR


class FormatChoiceInfo(BaseModel):
    key: str
    label: str


class FormatOptionInfo(BaseModel):
    key: str
    label: str
    help: str
    default: str
    choices: list[FormatChoiceInfo]


class FormatInfo(BaseModel):
    key: str
    name: str
    description: str
    renderers: list[str]
    options: list[FormatOptionInfo] = Field(default_factory=list)


class AudienceInfo(BaseModel):
    key: str
    name: str


class ControlInfo(BaseModel):
    key: str
    name: str
    description: str


class CatalogOut(BaseModel):
    """What the Studio page offers. Driven by the registries, never hardcoded."""

    formats: list[FormatInfo]
    audiences: list[AudienceInfo]
    languages: dict[str, str]
    tones: list[ControlInfo]
    detail_levels: list[ControlInfo]
    objectives: list[ControlInfo]
    styles: list[ControlInfo]
    defaults: dict[str, str]


class SendEmailRequest(BaseModel):
    to_email: str
    cc_emails: list[str] | None = None
    note: str | None = None


class SendEmailResponse(BaseModel):
    success: bool
    recipient: str
    subject: str
    message_id: str
    sent_at: str
    delivery_mode: str
    detail: str

