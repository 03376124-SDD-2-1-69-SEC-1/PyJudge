"""Behavior tests for the in-memory vector repository adapter."""

import pytest

from greader.ai.app.models import NewKnowledgeChunk, NewKnowledgeSource
from greader.ai.app.repository import (
    DuplicateChunkError,
    DuplicateSourceError,
    InMemoryVectorRepository,
)
from greader.ai.app.service import VectorService

MODEL_A = "model-a"
MODEL_B = "model-b"


def _embedding(first: float = 1.0, second: float = 0.0) -> tuple[float, ...]:
    return (first, second, *(0.0 for _ in range(766)))


def _source(core_document_id: int, model: str = MODEL_A) -> NewKnowledgeSource:
    return NewKnowledgeSource(
        core_document_id=core_document_id,
        r2_object_key=f"documents/{core_document_id}.pdf",
        content_hash=f"source-{core_document_id}",
        embedding_model=model,
        embedding_dim=768,
    )


def _chunk(
    index: int,
    embedding: tuple[float, ...] | None,
    *,
    model: str | None = MODEL_A,
    content_hash: str | None = None,
) -> NewKnowledgeChunk:
    return NewKnowledgeChunk(
        chunk_index=index,
        page=index + 1,
        text=f"chunk {index} for {model}",
        content_hash=content_hash or f"chunk-{index}",
        embedding_model=model,
        embedding=embedding,
    )


def test_search_returns_expected_fields_and_similarity_score() -> None:
    service = VectorService(InMemoryVectorRepository())
    created = service.create_source_with_chunks(_source(1), (_chunk(0, _embedding()),))

    results = service.search(_embedding(), embedding_model=MODEL_A, top_k=1)

    assert len(results) == 1
    assert results[0].chunk_id == created.chunks[0].id
    assert results[0].source_id == created.source.id
    assert results[0].page == 1
    assert results[0].text == "chunk 0 for model-a"
    assert results[0].score == pytest.approx(1.0)


def test_search_ranks_by_cosine_similarity() -> None:
    service = VectorService(InMemoryVectorRepository())
    service.create_source_with_chunks(
        _source(1),
        (
            _chunk(0, _embedding(0.0, 1.0)),
            _chunk(1, _embedding(0.8, 0.6)),
            _chunk(2, _embedding(1.0, 0.0)),
        ),
    )

    results = service.search(_embedding(), embedding_model=MODEL_A, top_k=3)

    assert [result.text for result in results] == [
        "chunk 2 for model-a",
        "chunk 1 for model-a",
        "chunk 0 for model-a",
    ]


def test_equal_scores_use_ascending_chunk_id() -> None:
    service = VectorService(InMemoryVectorRepository())
    created = service.create_source_with_chunks(
        _source(1),
        (_chunk(0, _embedding()), _chunk(1, _embedding())),
    )

    results = service.search(_embedding(), embedding_model=MODEL_A, top_k=2)

    assert [result.chunk_id for result in results] == [
        created.chunks[0].id,
        created.chunks[1].id,
    ]


def test_search_isolates_embedding_models() -> None:
    service = VectorService(InMemoryVectorRepository())
    service.create_source_with_chunks(
        _source(1, MODEL_A), (_chunk(0, _embedding(), model=MODEL_A),)
    )
    service.create_source_with_chunks(
        _source(2, MODEL_B), (_chunk(0, _embedding(), model=MODEL_B),)
    )

    results = service.search(_embedding(), embedding_model=MODEL_B, top_k=10)

    assert [result.text for result in results] == ["chunk 0 for model-b"]


def test_search_excludes_chunks_without_embeddings() -> None:
    service = VectorService(InMemoryVectorRepository())
    service.create_source_with_chunks(
        _source(1),
        (
            _chunk(0, None, model=None),
            _chunk(1, _embedding()),
        ),
    )

    results = service.search(_embedding(), embedding_model=MODEL_A, top_k=10)

    assert [result.text for result in results] == ["chunk 1 for model-a"]


def test_search_returns_empty_list_when_nothing_matches() -> None:
    service = VectorService(InMemoryVectorRepository())

    assert service.search(_embedding(), embedding_model=MODEL_A, top_k=10) == []


def test_duplicate_source_raises_contract_error() -> None:
    repository = InMemoryVectorRepository()
    repository.create_source_with_chunks(_source(1), ())

    with pytest.raises(DuplicateSourceError):
        repository.create_source_with_chunks(_source(1), ())


def test_duplicate_chunks_roll_back_source_and_all_ids() -> None:
    repository = InMemoryVectorRepository()
    duplicate_chunks = (
        _chunk(0, _embedding(), content_hash="same-hash"),
        _chunk(1, _embedding(), content_hash="same-hash"),
    )

    with pytest.raises(DuplicateChunkError):
        repository.create_source_with_chunks(_source(1), duplicate_chunks)

    created = repository.create_source_with_chunks(
        _source(1), (_chunk(0, _embedding()),)
    )
    assert created.source.id == 1
    assert created.chunks[0].id == 1
