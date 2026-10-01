"""output communication controls

Revision ID: b7c2e91d4a10
Revises: 84614ba3fa17
Create Date: 2026-10-01 10:00:00.000000

The new output types (linkedin, infographic, video) need no schema change:
output_type is a non-native enum stored as VARCHAR without a CHECK constraint,
and no new key is longer than the existing column.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b7c2e91d4a10"
down_revision = "84614ba3fa17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "outputs",
        sa.Column(
            "controls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("outputs", "controls")
