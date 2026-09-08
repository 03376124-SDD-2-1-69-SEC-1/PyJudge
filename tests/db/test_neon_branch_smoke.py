"""Canary proving CI really reached a migrated Neon branch.

Every other `postgres` test trusts that the branch exists, carries the schema,
and has pgvector installed. This file is what checks that assumption, so a
broken branch step shows up here instead of as a suite of vacuous passes.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def connection(postgres_url: str):
    engine = create_engine(postgres_url)
    try:
        with engine.connect() as open_connection:
            yield open_connection
    finally:
        engine.dispose()


def test_connects_through_psycopg_v3(connection: Connection) -> None:
    assert connection.engine.dialect.driver == "psycopg"
    assert connection.execute(text("SELECT 1")).scalar() == 1


def test_pgvector_extension_is_installed(connection: Connection) -> None:
    installed = connection.execute(
        text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
    ).scalar()
    assert installed == 1


def test_both_schemas_exist(connection: Connection) -> None:
    schemas = set(
        connection.execute(
            text("SELECT nspname FROM pg_namespace WHERE nspname IN ('core', 'rag')")
        ).scalars()
    )
    assert schemas == {"core", "rag"}


def test_rag_tables_exist(connection: Connection) -> None:
    tables = set(
        connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'rag'")
        ).scalars()
    )
    assert {"knowledge_sources", "knowledge_chunks"} <= tables


def test_hnsw_index_exists(connection: Connection) -> None:
    """The index alembic writes by hand; autogenerate cannot produce it."""
    definition = connection.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = 'rag' "
            "AND indexname = 'ix_knowledge_chunks_embedding_hnsw'"
        )
    ).scalar()
    assert definition is not None
    assert "hnsw" in definition
    assert "vector_cosine_ops" in definition
