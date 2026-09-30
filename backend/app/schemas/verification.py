from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClaimEvidenceOut(BaseModel):
    block_id: uuid.UUID
    page_no: int
    section_path: str
    quote: str
    similarity: float | None


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: str
    text: str
    cited_fact_ids: list[uuid.UUID]
    verdict: str | None
    score: float | None
    rationale: str | None
    evidence: list[ClaimEvidenceOut] = Field(default_factory=list)


class VerificationSummary(BaseModel):
    output_id: uuid.UUID
    status: str
    trust_score: float | None
    verified_at: datetime | None
    counts: dict[str, int]
    blocking_reasons: list[str]
    claims: list[ClaimOut]


class MatrixCell(BaseModel):
    output_id: uuid.UUID
    stated: str | None
    agrees: bool | None
    snippet: str


class MatrixRowOut(BaseModel):
    fact_id: uuid.UUID
    key: str
    statement: str
    expected: str | None
    unit: str | None
    has_mismatch: bool
    cells: list[MatrixCell]


class UnsourcedOut(BaseModel):
    output_id: uuid.UUID
    value: str
    snippet: str


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    fact_id: uuid.UUID | None
    severity: str
    expected_value: str | None
    observed: dict
    status: str
    note: str | None
    created_at: datetime


class OutputColumn(BaseModel):
    id: uuid.UUID
    type: str
    audience: str
    language: str
    version: int
    trust_score: float | None


class ConsistencyReport(BaseModel):
    """The facts x outputs grid, computed live from the current ContentIR."""

    document_id: uuid.UUID
    outputs: list[OutputColumn]
    rows: list[MatrixRowOut]
    unsourced: list[UnsourcedOut]
    issues: list[IssueOut]


class IssueUpdate(BaseModel):
    status: str = Field(pattern="^(open|resolved|accepted)$")
    note: str | None = None
