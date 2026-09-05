"""PostgreSQL vector adapter tests using mocked synchronous sessions."""

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError

from greader.ai.app.models import NewKnowledgeChunk, NewKnowledgeSource
from greader.ai.app.repository import (
    DuplicateChunkError,
    DuplicateSourceError,
    VectorRepositoryError,
)
from greader.ai.database.vector_repository import PostgresVectorRepository

MODEL = "model-a"


def _embedding() -> tuple[float, ...]:
    return (1.0, *(0.0 for _ in range(767)))


def _source() -> NewKnowledgeSource:
    return NewKnowledgeSource(
        core_document_id=7,
        r2_object_key="documents/7.pdf",
        content_hash="source-hash",
        embedding_model=MODEL,
        embedding_dim=768,
        metadata={"topic": "graphs"},
    )


def _chunk(index: int = 0) -> NewKnowledgeChunk:
    return NewKnowledgeChunk(
        chunk_index=index,
        page=index + 1,
        text=f"chunk {index}",
        token_count=2,
        content_hash=f"chunk-{index}",
        embedding_model=MODEL,
        metadata={"content_type": "lesson"},
        embedding=_embedding(),
    )


def _source_row() -> dict[str, object]:
    return {
        "id": 11,
        "core_document_id": 7,
        "r2_object_key": "documents/7.pdf",
        "content_hash": "source-hash",
        "status": "pending",
        "embedding_model": MODEL,
        "embedding_dim": 768,
        "metadata": {"topic": "graphs"},
    }


def _chunk_row(index: int = 0) -> dict[str, object]:
    return {
        "id": 21 + index,
        "source_id": 11,
        "chunk_index": index,
        "page": index + 1,
        "text": f"chunk {index}",
        "token_count": 2,
        "content_hash": f"chunk-{index}",
        "embedding_model": MODEL,
        "metadata": {"content_type": "lesson"},
        "embedding": list(_embedding()),
    }


def _result_for_one(row: dict[str, object]) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.one.return_value = row
    return result


def _repository(session: MagicMock) -> PostgresVectorRepository:
    @contextmanager
    def session_factory():
        yield session

    return PostgresVectorRepository(session_factory)


def _integrity_error(constraint_name: str) -> IntegrityError:
    original = Exception("database constraint")
    original.diag = MagicMock(constraint_name=constraint_name)  # type: ignore[attr-defined]
    return IntegrityError("INSERT", {}, original)


def test_creates_source_and_chunks_in_one_commit() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        _result_for_one(_source_row()),
        _result_for_one(_chunk_row(0)),
        _result_for_one(_chunk_row(1)),
    ]

    result = _repository(session).create_source_with_chunks(
        _source(), (_chunk(0), _chunk(1))
    )

    assert result.source.id == 11
    assert [chunk.id for chunk in result.chunks] == [21, 22]
    assert {chunk.source_id for chunk in result.chunks} == {11}
    assert session.execute.call_count == 3
    source_params = session.execute.call_args_list[0].args[0].compile().params
    first_chunk_params = session.execute.call_args_list[1].args[0].compile().params
    assert source_params["core_document_id"] == 7
    assert source_params["metadata"] == {"topic": "graphs"}
    assert first_chunk_params["source_id"] == 11
    assert first_chunk_params["embedding"] == list(_embedding())
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


@pytest.mark.parametrize(
    ("constraint_name", "expected_error"),
    [
        ("uq_knowledge_sources_core_document_id", DuplicateSourceError),
        ("uq_knowledge_chunks_source_content_hash", DuplicateChunkError),
    ],
)
def test_translates_unique_constraints_and_rolls_back(
    constraint_name: str, expected_error: type[VectorRepositoryError]
) -> None:
    session = MagicMock()
    error = _integrity_error(constraint_name)
    if expected_error is DuplicateChunkError:
        session.execute.side_effect = [_result_for_one(_source_row()), error]
    else:
        session.execute.side_effect = error

    with pytest.raises(expected_error):
        _repository(session).create_source_with_chunks(_source(), (_chunk(),))

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_translates_unknown_database_write_failure_and_rolls_back() -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError("INSERT", {}, Exception("offline"))

    with pytest.raises(VectorRepositoryError, match="storage operation failed"):
        _repository(session).create_source_with_chunks(_source(), ())

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_search_maps_results_and_builds_model_scoped_ordered_query() -> None:
    session = MagicMock()
    search_result = MagicMock()
    search_result.mappings.return_value.all.return_value = [
        {
            "chunk_id": 21,
            "source_id": 11,
            "page": 1,
            "text": "chunk 0",
            "score": 0.75,
        }
    ]
    session.execute.return_value = search_result

    results = _repository(session).search(_embedding(), embedding_model=MODEL, limit=5)

    assert results[0].chunk_id == 21
    assert results[0].score == 0.75
    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "knowledge_chunks.embedding IS NOT NULL" in sql
    assert "knowledge_chunks.embedding_model =" in sql
    assert " <=> " in sql
    assert " AS score" in sql
    assert "ORDER BY score DESC, rag.knowledge_chunks.id ASC" in sql
    assert "LIMIT" in sql


def test_search_returns_empty_list() -> None:
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = []

    assert (
        _repository(session).search(_embedding(), embedding_model=MODEL, limit=5) == []
    )


def test_search_translates_database_failure() -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError("SELECT", {}, Exception("offline"))

    with pytest.raises(VectorRepositoryError, match="search operation failed"):
        _repository(session).search(_embedding(), embedding_model=MODEL, limit=5)

    session.rollback.assert_called_once_with()
