"""Relational schema.

`document_blocks.id` is the single traceability primitive: facts, claims and
citations all ultimately point at a block, which knows its page, section and
bounding box. Nothing in the system cites free-floating text.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB, UUID as PGUUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
JSONB = JSON().with_variant(PG_JSONB(), "postgresql")
def ARRAY(item_type):
    return JSON().with_variant(PG_ARRAY(item_type), "postgresql")


# --- enumerations (stored as VARCHAR + CHECK, so migrations stay painless) ---

# Access level. Separate from the job role, which decides which outputs a
# person may create; "admin" manages employees and roles.
UserRole = Enum("editor", "approver", "admin", name="user_role", native_enum=False)
DocumentStatus = Enum(
    "uploaded",
    "parsing",
    "parsed",
    "indexing",
    "indexed",
    "extracting",
    "ready",
    "failed",
    name="document_status",
    native_enum=False,
)
BlockType = Enum(
    "heading",
    "paragraph",
    "list_item",
    "table",
    "caption",
    "footer",
    "slide_text",
    name="block_type",
    native_enum=False,
)
JobKind = Enum(
    "ingest", "index", "extract", "generate", "verify", name="job_kind", native_enum=False
)
JobStatus = Enum("queued", "running", "succeeded", "failed", name="job_status", native_enum=False)
FactType = Enum(
    "metric",
    "date",
    "entity",
    "finding",
    "recommendation",
    "risk",
    name="fact_type",
    native_enum=False,
)
OutputType = Enum(
    "advisory",
    "ppt",
    "summary",
    "email",
    "linkedin",
    "twitter",
    "press_release",
    "report",
    "infographic",
    "video",
    # Legacy key from before the LinkedIn rename; kept so old rows still load.
    "social",
    name="output_type",
    native_enum=False,
)
Audience = Enum(
    "officer",
    "management",
    "technical",
    "public",
    "social",
    name="audience",
    native_enum=False,
)
OutputStatus = Enum(
    "draft",
    "verified",
    "in_review",
    "approved",
    "rejected",
    "exported",
    name="output_status",
    native_enum=False,
)
Verdict = Enum(
    "supported",
    "partial",
    "unsupported",
    "contradicted",
    name="verdict",
    native_enum=False,
)
IssueStatus = Enum("open", "resolved", "accepted", name="issue_status", native_enum=False)
IssueKind = Enum("value_mismatch", "unsourced_number", name="issue_kind", native_enum=False)
Severity = Enum("low", "medium", "high", name="severity", native_enum=False)
ReviewAction = Enum("comment", "edit", "approve", "reject", name="review_action", native_enum=False)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


class JobRole(Base, TimestampMixin):
    """A job in the organisation and the output types it may create."""

    __tablename__ = "job_roles"

    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Output type keys, e.g. ["linkedin", "twitter"].
    allowed_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(UserRole, nullable=False, default="editor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # None means no job role yet: the person may create every output type.
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_roles.id", ondelete="SET NULL"), index=True
    )
    job_role: Mapped[JobRole | None] = relationship(lazy="joined")


# --------------------------------------------------------------------------
# Source documents and their traceability anchors
# --------------------------------------------------------------------------


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = _pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_lang: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    status: Mapped[str] = mapped_column(DocumentStatus, nullable=False, default="uploaded")
    error: Mapped[str | None] = mapped_column(Text)

    blocks: Mapped[list[DocumentBlock]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentBlock(Base):
    """One addressable piece of the source. THE traceability anchor."""

    __tablename__ = "document_blocks"
    __table_args__ = (
        Index("ix_blocks_doc_page", "document_id", "page_no"),
        UniqueConstraint("document_id", "order_idx", name="uq_block_order"),
    )

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    section_path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    order_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[str] = mapped_column(BlockType, nullable=False, default="paragraph")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # [x0, y0, x1, y1] in PDF points; null for docx/pptx where there is no box.
    bbox: Mapped[dict | None] = mapped_column(JSONB)

    document: Mapped[Document] = relationship(back_populates="blocks")


class Chunk(Base):
    """Retrieval unit. Never spans a section; remembers the blocks it came from."""

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(PGUUID(as_uuid=True)), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qdrant_point_id: Mapped[str] = mapped_column(String(64), nullable=False)


# --------------------------------------------------------------------------
# Pipeline jobs
# --------------------------------------------------------------------------


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(JobKind, nullable=False)
    status: Mapped[str] = mapped_column(JobStatus, nullable=False, default="queued")
    stage: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------
# Source of Truth
# --------------------------------------------------------------------------


class FactSheet(Base, TimestampMixin):
    __tablename__ = "fact_sheets"
    __table_args__ = (UniqueConstraint("document_id", "version", name="uq_factsheet_version"),)

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    summary: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    facts: Mapped[list[Fact]] = relationship(
        back_populates="fact_sheet", cascade="all, delete-orphan"
    )


class Fact(Base):
    """A normalized unit of truth. Numbers are canonicalized exactly once, here."""

    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = _pk()
    fact_sheet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fact_sheets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(FactType, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    # Canonical form used by the deterministic consistency checker.
    canonical_value: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    # Alternate surface forms an output might legitimately use ("thirty-seven").
    aliases: Mapped[list | None] = mapped_column(JSONB)
    edited_by_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    fact_sheet: Mapped[FactSheet] = relationship(back_populates="facts")
    evidence: Mapped[list[FactEvidence]] = relationship(
        back_populates="fact", cascade="all, delete-orphan"
    )


class FactEvidence(Base):
    __tablename__ = "fact_evidence"

    id: Mapped[uuid.UUID] = _pk()
    fact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_blocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)

    fact: Mapped[Fact] = relationship(back_populates="evidence")


# --------------------------------------------------------------------------
# Generated outputs
# --------------------------------------------------------------------------


class Output(Base, TimestampMixin):
    __tablename__ = "outputs"

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fact_sheet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fact_sheets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(OutputType, nullable=False)
    audience: Mapped[str] = mapped_column(Audience, nullable=False, default="officer")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    # Tone, detail level, objective and style this output was generated with.
    controls: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(OutputStatus, nullable=False, default="draft")
    # The format-neutral node tree every renderer consumes.
    content_ir: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trust_score: Mapped[float | None] = mapped_column(Float)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    claims: Mapped[list[OutputClaim]] = relationship(
        back_populates="output", cascade="all, delete-orphan"
    )


class OutputClaim(Base):
    __tablename__ = "output_claims"

    id: Mapped[uuid.UUID] = _pk()
    output_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outputs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    cited_fact_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list
    )
    verdict: Mapped[str | None] = mapped_column(Verdict)
    score: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[str | None] = mapped_column(Text)

    output: Mapped[Output] = relationship(back_populates="claims")


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    id: Mapped[uuid.UUID] = _pk()
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("output_claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_blocks.id", ondelete="CASCADE"), nullable=False
    )
    similarity: Mapped[float | None] = mapped_column(Float)


class ConsistencyIssue(Base, TimestampMixin):
    """A fact whose value disagrees across outputs, or against the source."""

    __tablename__ = "consistency_issues"

    id: Mapped[uuid.UUID] = _pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(IssueKind, nullable=False, default="value_mismatch")
    # Null for an unsourced number: the output stated a figure that belongs to
    # no fact at all, so there is nothing to point at.
    fact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"))
    severity: Mapped[str] = mapped_column(Severity, nullable=False, default="high")
    expected_value: Mapped[str | None] = mapped_column(String(255))
    # {output_id: observed_value} — drives the facts x outputs matrix in the UI.
    observed: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(IssueStatus, nullable=False, default="open")
    note: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------
# Review, export, audit
# --------------------------------------------------------------------------


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = _pk()
    output_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outputs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(ReviewAction, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class Export(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = _pk()
    output_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outputs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"
    __table_args__ = (CheckConstraint("length(entity) > 0", name="ck_audit_entity_nonempty"),)

    id: Mapped[uuid.UUID] = _pk()
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
