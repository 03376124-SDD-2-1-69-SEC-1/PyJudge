"""PostgreSQL vector adapter tests using mocked synchronous sessions.

These tests verify mapping, transaction calls, and PostgreSQL query construction.
They do not verify real PostgreSQL persistence or pgvector execution.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from greader.ai.app.models import (
    ChunkSearchResult,
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)
from greader.ai.app.repository import (
    DuplicateChunkError,
    DuplicateSourceError,
    VectorRepositoryError,
    VectorRepositoryUnavailableError,
)
from greader.database.rag.vector_repository import PostgresVectorRepository

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


def _result_for_many(rows: list[dict[str, object]]) -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
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
        _result_for_many([_chunk_row(1), _chunk_row(0)]),
    ]

    result = _repository(session).create_source_with_chunks(
        _source(), (_chunk(0), _chunk(1))
    )

    assert result == SourceCreationResult(
        source=KnowledgeSource(
            id=11,
            core_document_id=7,
            r2_object_key="documents/7.pdf",
            content_hash="source-hash",
            status="pending",
            embedding_model=MODEL,
            embedding_dim=768,
            metadata={"topic": "graphs"},
        ),
        chunks=(
            KnowledgeChunk(
                id=21,
                source_id=11,
                chunk_index=0,
                page=1,
                text="chunk 0",
                token_count=2,
                content_hash="chunk-0",
                embedding_model=MODEL,
                metadata={"content_type": "lesson"},
                embedding=_embedding(),
            ),
            KnowledgeChunk(
                id=22,
                source_id=11,
                chunk_index=1,
                page=2,
                text="chunk 1",
                token_count=2,
                content_hash="chunk-1",
                embedding_model=MODEL,
                metadata={"content_type": "lesson"},
                embedding=_embedding(),
            ),
        ),
    )
    assert session.execute.call_count == 2
    source_params = session.execute.call_args_list[0].args[0].compile().params
    first_chunk_params = session.execute.call_args_list[1].args[0].compile().params
    assert source_params == {
        "content_hash": "source-hash",
        "core_document_id": 7,
        "embedding_dim": 768,
        "embedding_model": MODEL,
        "metadata": {"topic": "graphs"},
        "r2_object_key": "documents/7.pdf",
        "status": "pending",
    }
    for index in (0, 1):
        expected = _chunk_row(index)
        expected.pop("id")
        assert {
            key.removesuffix(f"_m{index}"): value
            for key, value in first_chunk_params.items()
            if key.endswith(f"_m{index}")
        } == expected
    session.flush.assert_not_called()
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_batch_preserves_input_order_independent_of_index_and_returning_order():
    session = MagicMock()
    session.execute.side_effect = [
        _result_for_one(_source_row()),
        _result_for_many([_chunk_row(0), _chunk_row(2), _chunk_row(1)]),
    ]
    result = _repository(session).create_source_with_chunks(
        _source(), (_chunk(2), _chunk(0), _chunk(1))
    )
    assert [chunk.content_hash for chunk in result.chunks] == [
        "chunk-2",
        "chunk-0",
        "chunk-1",
    ]
    assert [chunk.id for chunk in result.chunks] == [23, 21, 22]
    assert session.execute.call_count == 2


def test_two_thousand_chunks_use_one_batch_statement():
    session = MagicMock()
    session.execute.side_effect = [
        _result_for_one(_source_row()),
        _result_for_many([_chunk_row(index) for index in reversed(range(2000))]),
    ]
    chunks = tuple(_chunk(index) for index in range(2000))
    result = _repository(session).create_source_with_chunks(_source(), chunks)
    assert len(result.chunks) == 2000
    assert [chunk.content_hash for chunk in result.chunks] == [
        chunk.content_hash for chunk in chunks
    ]
    assert session.execute.call_count == 2
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert str(compiled).count("INSERT INTO") == 1
    assert "RETURNING" in str(compiled)
    assert compiled.params["content_hash_m1999"] == "chunk-1999"
    session.commit.assert_called_once_with()


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


def test_chunk_database_failure_rolls_back_source_and_does_not_commit() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        _result_for_one(_source_row()),
        OperationalError("INSERT", {}, Exception("offline")),
    ]

    with pytest.raises(
        VectorRepositoryUnavailableError, match="storage operation failed"
    ):
        _repository(session).create_source_with_chunks(_source(), (_chunk(),))

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


def test_translates_unrecognized_integrity_error_without_exposing_sqlalchemy() -> None:
    session = MagicMock()
    session.execute.side_effect = _integrity_error("unexpected_constraint")

    with pytest.raises(
        VectorRepositoryError, match="storage integrity constraint failed"
    ) as raised:
        _repository(session).create_source_with_chunks(_source(), ())

    assert not isinstance(raised.value, IntegrityError)
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
            "distance": 0.25,
        }
    ]
    session.execute.return_value = search_result

    results = _repository(session).search(_embedding(), embedding_model=MODEL, limit=5)

    assert results == [
        ChunkSearchResult(
            chunk_id=21,
            source_id=11,
            page=1,
            text="chunk 0",
            score=0.75,
        )
    ]
    statement = session.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "knowledge_chunks.embedding IS NOT NULL" in sql
    assert "knowledge_chunks.embedding_model =" in sql
    assert " <=> " in sql
    assert " AS distance" in sql
    assert "ORDER BY distance ASC, rag.knowledge_chunks.id ASC" in sql
    assert "DESC" not in sql
    assert " - " not in sql
    assert "LIMIT" in sql
    assert MODEL in compiled.params.values()
    assert list(_embedding()) in compiled.params.values()
    assert 5 in compiled.params.values()


@pytest.mark.parametrize("distance", [0.0, 0.25, 1.0, 2.0])
def test_search_converts_cosine_distance_to_similarity(distance: float) -> None:
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "chunk_id": 1,
            "source_id": 2,
            "page": None,
            "text": "text",
            "distance": distance,
        }
    ]
    results = _repository(session).search(_embedding(), embedding_model=MODEL, limit=1)
    assert results[0].score == pytest.approx(1.0 - distance)


def test_search_returns_empty_list() -> None:
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = []

    assert (
        _repository(session).search(_embedding(), embedding_model=MODEL, limit=5) == []
    )


def test_search_translates_database_failure() -> None:
    session = MagicMock()
    session.execute.side_effect = OperationalError("SELECT", {}, Exception("offline"))

    with pytest.raises(
        VectorRepositoryUnavailableError, match="search operation failed"
    ):
        _repository(session).search(_embedding(), embedding_model=MODEL, limit=5)

    session.rollback.assert_called_once_with()


@pytest.mark.parametrize("operation", ["create", "search"])
@pytest.mark.parametrize("phase", ["open", "close", "rollback"])
def test_session_lifecycle_errors_do_not_escape_port(
    operation: str, phase: str
) -> None:
    error = OperationalError("private SQL", {}, Exception("offline"))
    session = MagicMock()
    session.execute.return_value = _result_for_one(_source_row())
    session.execute.return_value.mappings.return_value.all.return_value = []
    if phase == "rollback":
        session.execute.side_effect = error
        session.rollback.side_effect = error

    @contextmanager
    def factory():
        if phase == "open":
            raise error
        yield session
        if phase == "close":
            raise error

    repository = PostgresVectorRepository(factory)
    with pytest.raises(VectorRepositoryUnavailableError):
        if operation == "create":
            repository.create_source_with_chunks(_source(), ())
        else:
            repository.search(_embedding(), embedding_model=MODEL, limit=1)


def test_commit_failure_rolls_back_and_translates() -> None:
    session = MagicMock()
    session.execute.return_value = _result_for_one(_source_row())
    session.commit.side_effect = OperationalError("COMMIT", {}, Exception("offline"))
    with pytest.raises(VectorRepositoryUnavailableError):
        _repository(session).create_source_with_chunks(_source(), ())
    session.rollback.assert_called_once_with()


@pytest.mark.parametrize("operation", ["create", "search"])
@pytest.mark.parametrize("unexpected", [RuntimeError("bug"), TypeError("bug")])
def test_unexpected_exceptions_are_not_mislabeled_unavailable(operation, unexpected):
    session = MagicMock()
    session.execute.side_effect = unexpected
    repository = _repository(session)
    with pytest.raises(type(unexpected)) as raised:
        if operation == "create":
            repository.create_source_with_chunks(_source(), (_chunk(),))
        else:
            repository.search(_embedding(), embedding_model=MODEL, limit=1)
    assert raised.value is unexpected


def test_sql_programming_error_is_not_mislabeled_unavailable():
    session = MagicMock()
    session.execute.side_effect = ProgrammingError("private SQL", {}, Exception("bug"))
    with pytest.raises(VectorRepositoryError) as raised:
        _repository(session).search(_embedding(), embedding_model=MODEL, limit=1)
    assert not isinstance(raised.value, VectorRepositoryUnavailableError)
    session.rollback.assert_called_once_with()
