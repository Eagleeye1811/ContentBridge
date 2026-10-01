"""job roles and per-role outputs

Revision ID: c41f2a7e9b03
Revises: b7c2e91d4a10
Create Date: 2026-10-02 10:00:00.000000

Adds job roles (each listing the output types it may create), links users to
one, and seeds a starting set. The "admin" access level and the "twitter"
output type need no schema change: both enums are VARCHAR without a CHECK
constraint, and neither value is longer than the existing columns.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c41f2a7e9b03"
down_revision = "b7c2e91d4a10"
branch_labels = None
depends_on = None

# Kept inline so the migration does not depend on application code.
DEFAULT_ROLES = [
    (
        "Social Media Analyst",
        "Runs the organisation's public social media presence.",
        ["linkedin", "twitter", "infographic", "video"],
    ),
    (
        "Public Relations Officer",
        "Handles statements to the press and the public.",
        ["press_release", "linkedin", "twitter", "email"],
    ),
    (
        "Research Analyst",
        "Turns technical findings into reports and briefings.",
        ["report", "summary", "advisory"],
    ),
    (
        "Cyber Security Analyst",
        "Issues security advisories and incident reports.",
        ["advisory", "report", "email"],
    ),
    (
        "Training & Outreach Officer",
        "Prepares training and awareness material.",
        ["ppt", "video", "infographic"],
    ),
    (
        "Senior Management",
        "Needs short briefings and decks for decisions.",
        ["summary", "ppt", "report"],
    ),
]


def upgrade() -> None:
    roles = op.create_table(
        "job_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "allowed_types",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.add_column("users", sa.Column("job_role_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_users_job_role_id"), "users", ["job_role_id"], unique=False)
    op.create_foreign_key(
        "fk_users_job_role_id", "users", "job_roles", ["job_role_id"], ["id"], ondelete="SET NULL"
    )
    op.bulk_insert(
        roles,
        [
            {"id": uuid.uuid4(), "name": n, "description": d, "allowed_types": t}
            for n, d, t in DEFAULT_ROLES
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_job_role_id", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_job_role_id"), table_name="users")
    op.drop_column("users", "job_role_id")
    op.drop_table("job_roles")
