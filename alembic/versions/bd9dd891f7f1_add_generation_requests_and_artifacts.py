"""add generation requests and artifacts

Revision ID: bd9dd891f7f1
Revises: 35927253f62b
Create Date: 2026-07-22 09:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd9dd891f7f1"
down_revision: str | Sequence[str] | None = "35927253f62b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "generation_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("generation_mode", sa.String(length=50), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("safe_error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["assignments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generation_requests", schema=None) as batch_op:
        batch_op.create_index(
            "ix_generation_requests_assignment_id", ["assignment_id"], unique=False
        )
        batch_op.create_index("ix_generation_requests_status", ["status"], unique=False)

    op.create_table(
        "generation_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("generation_request_id", sa.String(length=36), nullable=False),
        sa.Column("generation_mode", sa.String(length=50), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("is_applied", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["generation_request_id"],
            ["generation_requests.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_request_id"),
    )
    with op.batch_alter_table("generation_artifacts", schema=None) as batch_op:
        batch_op.create_index(
            "ix_generation_artifacts_generation_request_id",
            ["generation_request_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("generation_artifacts", schema=None) as batch_op:
        batch_op.drop_index("ix_generation_artifacts_generation_request_id")
    op.drop_table("generation_artifacts")

    with op.batch_alter_table("generation_requests", schema=None) as batch_op:
        batch_op.drop_index("ix_generation_requests_status")
        batch_op.drop_index("ix_generation_requests_assignment_id")
    op.drop_table("generation_requests")
