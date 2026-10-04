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
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("job_role_id", sa.UUID(), nullable=True))
        batch_op.create_index(op.f("ix_users_job_role_id"), ["job_role_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_users_job_role_id", "job_roles", ["job_role_id"], ["id"], ondelete="SET NULL"
        )
    op.bulk_insert(
        roles,
        [
            {"id": uuid.uuid4(), "name": n, "description": d, "allowed_types": t}
            for n, d, t in DEFAULT_ROLES
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_job_role_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_users_job_role_id"))
        batch_op.drop_column("job_role_id")
    op.drop_table("job_roles")
