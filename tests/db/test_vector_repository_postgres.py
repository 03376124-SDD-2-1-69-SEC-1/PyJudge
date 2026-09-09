"""AI-01 HTTP round trips against OPS-09's isolated PostgreSQL database."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, delete, select
from sqlmodel import Session

from greader.database.rag.tables import KnowledgeSource
from greader.database.rag.vector_repository import PostgresVectorRepository
from greader.main import create_app

pytestmark = pytest.mark.postgres
SOURCE_TABLE = KnowledgeSource.__table__


def _vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * 766)]


@pytest.fixture()
def vector_case(postgres_url: str):
    engine = create_engine(postgres_url)
    marker = f"ai01-{uuid.uuid4().hex}"
    document_id = uuid.uuid4().int % (2**63 - 1) + 1
    try:
        yield engine, marker, document_id
    finally:
        try:
            with engine.begin() as connection:
                # The exact per-test marker prevents deleting any pre-existing row
                # even in the extremely unlikely event of a document ID collision.
                connection.execute(
                    delete(SOURCE_TABLE).where(
                        SOURCE_TABLE.c.core_document_id == document_id,
                        SOURCE_TABLE.c.r2_object_key == marker,
                        SOURCE_TABLE.c.metadata["ai01_test"].astext == marker,
                    )
                )
        finally:
            engine.dispose()


@pytest.fixture()
async def client(vector_case):
    engine, _, _ = vector_case
    application = create_app(
        vector_repository=PostgresVectorRepository(lambda: Session(engine))
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as test_client:
        yield test_client


def _payload(vector_case, embeddings):
    _, marker, document_id = vector_case
    return {
        "core_document_id": document_id,
        "r2_object_key": marker,
        "content_hash": marker,
        "embedding_model": marker,
        "embedding_dim": 768,
        "metadata": {"ai01_test": marker},
        "chunks": [
            {
                "chunk_index": index,
                "page": index + 1,
                "text": f"{marker} chunk {index}",
                "content_hash": f"{marker}-{index}",
                "embedding_model": marker,
                "embedding": embedding,
            }
            for index, embedding in enumerate(embeddings)
        ],
    }


def _query(model):
    return {"embedding": _vector(1.0), "embedding_model": model, "top_k": 10}


@pytest.mark.anyio
async def test_http_insert_and_search_round_trip_preserves_chunk_order(
    client, vector_case
):
    payload = _payload(vector_case, [_vector(1.0), _vector(0.0, 1.0), _vector(-1.0)])
    # Repeated, unsorted indices must not be used to reconstruct INSERT order.
    for chunk, index in zip(payload["chunks"], [7, 2, 7], strict=True):
        chunk["chunk_index"] = index
    response = await client.post("/api/v1/knowledge-sources", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert isinstance(created["source"]["id"], int)
    assert [chunk["content_hash"] for chunk in created["chunks"]] == [
        chunk["content_hash"] for chunk in payload["chunks"]
    ]
    result = await client.post(
        "/api/v1/knowledge-chunks/search", json=_query(vector_case[1])
    )
    assert result.status_code == 200
    assert [match["chunk_id"] for match in result.json()] == [
        chunk["id"] for chunk in created["chunks"]
    ]
    assert result.json()[0] == {
        "chunk_id": created["chunks"][0]["id"],
        "source_id": created["source"]["id"],
        "page": payload["chunks"][0]["page"],
        "text": payload["chunks"][0]["text"],
        "score": pytest.approx(1.0),
    }


@pytest.mark.anyio
async def test_cosine_ranking_ties_and_null_exclusion(client, vector_case):
    payload = _payload(
        vector_case,
        [_vector(0.0, 1.0), _vector(-1.0), _vector(1.0), _vector(1.0), None],
    )
    response = await client.post("/api/v1/knowledge-sources", json=payload)
    assert response.status_code == 201
    chunks = response.json()["chunks"]
    response = await client.post(
        "/api/v1/knowledge-chunks/search", json=_query(vector_case[1])
    )
    assert response.status_code == 200
    matches = response.json()
    assert [match["chunk_id"] for match in matches] == [
        *sorted([chunks[2]["id"], chunks[3]["id"]]),
        chunks[0]["id"],
        chunks[1]["id"],
    ]
    assert [match["score"] for match in matches] == pytest.approx([1.0, 1.0, 0.0, -1.0])


@pytest.mark.anyio
async def test_duplicate_chunk_rolls_back_source_in_database(client, vector_case):
    engine, _, document_id = vector_case
    payload = _payload(vector_case, [_vector(1.0), _vector(1.0)])
    payload["chunks"][1]["content_hash"] = payload["chunks"][0]["content_hash"]
    response = await client.post("/api/v1/knowledge-sources", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "duplicate_knowledge_chunk"
    # Check from a separate connection, not the adapter's transaction or identity map.
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(SOURCE_TABLE.c.id).where(
                    SOURCE_TABLE.c.core_document_id == document_id
                )
            ).all()
            == []
        )
    retry = await client.post(
        "/api/v1/knowledge-sources", json=_payload(vector_case, [_vector(1.0)])
    )
    assert retry.status_code == 201


@pytest.mark.anyio
async def test_search_excludes_other_embedding_model(client, vector_case):
    response = await client.post(
        "/api/v1/knowledge-sources", json=_payload(vector_case, [_vector(1.0)])
    )
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/knowledge-chunks/search", json=_query(f"{vector_case[1]}-other")
    )
    assert response.status_code == 200
    assert response.json() == []
