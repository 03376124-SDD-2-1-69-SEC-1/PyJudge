"""add hnsw index on knowledge_chunks

Revision ID: a895b3b19051
Revises: 93cd0a90c897
Create Date: 2026-09-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a895b3b19051"
down_revision: Union[str, Sequence[str], None] = "93cd0a90c897"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw "
        "ON rag.knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS rag.ix_knowledge_chunks_embedding_hnsw")
