"""add core.topics table

Revision ID: d3b7c1e9a204
Revises: a895b3b19051
Create Date: 2026-09-19 00:00:00.000000

The Topics slice had no table: it kept UUID-keyed rows in process memory while
every other slice was persisted. This gives it a BIGSERIAL-keyed table like the
rest, so the API stops losing topics on restart (OPS-12).

The case-insensitive unique index is written by hand — autogenerate cannot
produce a functional index on `lower(name)`.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3b7c1e9a204"
down_revision: Union[str, Sequence[str], None] = "a895b3b19051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "topics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_topics_name_lower ON core.topics (lower(name))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS core.uq_topics_name_lower")
    op.drop_table("topics", schema="core")
