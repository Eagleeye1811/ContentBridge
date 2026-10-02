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
    options: dict[str, dict[str, str]] = Field(default_factory=dict)
    audience: str | None = None
    tone: str | None = None
    detail_level: str | None = None
    objective: str | None = None
    style: str | None = None
    controls_dict: dict[str, str] = Field(default_factory=dict, alias="controls")

    def controls(self) -> dict[str, str]:
        values = {
            "tone": self.tone,
            "detail_level": self.detail_level,
            "objective": self.objective,
            "style": self.style,
            **(self.controls_dict or {}),
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


class PresentationOutlineRequest(BaseModel):
    title: str | None = None
    purpose: str = "executive briefing"
    audience: str = "officials"
    slide_count: str = "auto"
    duration: str = "10"
    language: str = "en"
    content_detail: str = "balanced"
    theme: str = "navy_white"
    visual_preference: str = "balanced"
    speaker_notes: bool = True
    additional_instructions: str | None = None


class SlideOutlineItem(BaseModel):
    id: str
    title: str
    key_message: str
    summary: str
    suggested_layout: str = "standard_bullet"
    fact_ids: list[str] = Field(default_factory=list)


class PresentationOutlineResponse(BaseModel):
    title: str
    slides: list[SlideOutlineItem]


class SlideRegenerateRequest(BaseModel):
    instructions: str | None = None


class PresentationReconfigureRequest(BaseModel):
    config: PresentationOutlineRequest
    scope: str = "all"  # "all" or "selected"
    selected_slide_ids: list[str] = Field(default_factory=list)
    preserve_user_edits: bool = True
    content_ir: ContentIR | None = None


class PresentationReconfigureResponse(BaseModel):
    output: OutputDetail
    change_summary: list[str]
    proposed_outline: PresentationOutlineResponse | None = None
    warnings: list[str] = Field(default_factory=list)


class SlideCountAdjustRequest(BaseModel):
    target_count: str
    config: PresentationOutlineRequest


class PresentationRevertRequest(BaseModel):
    target_version: int | None = None
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

