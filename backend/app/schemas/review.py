from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    output_id: uuid.UUID
    user_id: uuid.UUID | None
    actor_name: str = ""
    actor_role: str = ""
    action: str
    note: str | None
    created_at: datetime


class ReviewAction(BaseModel):
    note: str | None = None


class RejectAction(BaseModel):
    # A rejection without a reason is not actionable for the editor.
    note: str = Field(min_length=3, max_length=2000)


class ApprovalState(BaseModel):
    """Everything the UI needs to decide what the reviewer may do next."""

    output_id: uuid.UUID
    status: str
    trust_score: float | None
    verified_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    approver_name: str | None
    blocking_reasons: list[str]
    can_submit: bool
    can_approve: bool
    can_reject: bool
    history: list[ReviewOut]


class PendingOutput(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    type: str
    audience: str
    language: str
    version: int
    status: str
    trust_score: float | None
    title: str
    submitted_at: datetime | None


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_name: str = ""
    entity: str
    entity_id: uuid.UUID | None
    action: str
    payload: dict | None
    created_at: datetime
