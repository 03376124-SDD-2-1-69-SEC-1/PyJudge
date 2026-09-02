"""add artifact review state

Revision ID: 4f2c9a71d8e3
Revises: bd9dd891f7f1
Create Date: 2026-09-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4f2c9a71d8e3"
down_revision: str | Sequence[str] | None = "bd9dd891f7f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace the ambiguous applied flag with an explicit review state."""
    with op.batch_alter_table("generation_artifacts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "review_status",
                sa.String(length=50),
                nullable=False,
                server_default="draft",
            )
        )
        batch_op.add_column(
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
        )

    artifacts = sa.table(
        "generation_artifacts",
        sa.column("is_applied", sa.Boolean()),
        sa.column("applied_at", sa.DateTime(timezone=True)),
        sa.column("review_status", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        artifacts.update()
        .where(artifacts.c.is_applied.is_(True))
        .values(review_status="applied", reviewed_at=artifacts.c.applied_at)
    )

    with op.batch_alter_table("generation_artifacts") as batch_op:
        batch_op.drop_column("is_applied")
        batch_op.drop_column("applied_at")


def downgrade() -> None:
    """Restore the legacy applied flag representation."""
    with op.batch_alter_table("generation_artifacts") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_applied",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True)
        )

    artifacts = sa.table(
        "generation_artifacts",
        sa.column("is_applied", sa.Boolean()),
        sa.column("applied_at", sa.DateTime(timezone=True)),
        sa.column("review_status", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        artifacts.update()
        .where(artifacts.c.review_status == "applied")
        .values(is_applied=True, applied_at=artifacts.c.reviewed_at)
    )

    with op.batch_alter_table("generation_artifacts") as batch_op:
        batch_op.drop_column("review_status")
        batch_op.drop_column("reviewed_at")
