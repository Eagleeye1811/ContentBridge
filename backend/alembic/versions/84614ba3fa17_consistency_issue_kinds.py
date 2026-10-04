"""consistency issue kinds

Revision ID: 84614ba3fa17
Revises: 4da49fdb1264
Create Date: 2026-09-30 23:31:39.547951
"""

import sqlalchemy as sa

from alembic import op

revision = "84614ba3fa17"
down_revision = "4da49fdb1264"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("consistency_issues") as batch_op:
        batch_op.add_column(
            sa.Column(
                "kind",
                sa.Enum("value_mismatch", "unsourced_number", name="issue_kind", native_enum=False),
                nullable=False,
            )
        )
        batch_op.alter_column("fact_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("consistency_issues") as batch_op:
        batch_op.alter_column("fact_id", existing_type=sa.UUID(), nullable=False)
        batch_op.drop_column("kind")
