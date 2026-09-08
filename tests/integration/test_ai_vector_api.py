"""HTTP integration tests for the standalone AI vector API."""

import importlib
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from greader.ai.app import main as ai_main
from greader.ai.app.models import (
    ChunkSearchResult,
    Embedding,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)
from greader.ai.app.repository import (
    InMemoryVectorRepository,
    VectorRepositoryError,
    VectorRepositoryUnavailableError,
)
from greader.ai.database import vector_repository as postgres_adapter

MODEL_A = "model-a"
MODEL_B = "model-b"


def _embedding(first: float = 1.0, second: float = 0.0) -> list[float]:
    return [first, second, *(0.0 for _ in range(766))]


def _source_payload(
    *,
    core_document_id: int = 1,
    model: str = MODEL_A,
    chunk_hashes: tuple[str, ...] = ("chunk-0",),
    embedding: list[float] | None = None,
) -> dict[str, object]:
    vector = embedding if embedding is not None else _embedding()
    return {
        "core_document_id": core_document_id,
        "r2_object_key": f"documents/{core_document_id}.pdf",
        "content_hash": f"source-{core_document_id}",
        "embedding_model": model,
        "embedding_dim": 768,
        "metadata": {"topic": "graphs"},
        "chunks": [
            {
                "chunk_index": index,
                "page": index + 1,
                "text": f"chunk {index} for {model}",
                "token_count": 4,
                "content_hash": content_hash,
                "embedding_model": model,
                "metadata": {"section": index},
                "embedding": vector,
            }
            for index, content_hash in enumerate(chunk_hashes)
        ],
    }


def _search_payload(*, model: str = MODEL_A, top_k: int = 10) -> dict[str, object]:
    return {
        "embedding": _embedding(),
        "embedding_model": model,
        "top_k": top_k,
    }


@pytest.fixture()
async def client() -> AsyncIterator[AsyncClient]:
    application = ai_main.create_app(repository=InMemoryVectorRepository())
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_create_returns_committed_source_and_chunk_without_vectors(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/knowledge-sources",
        json=_source_payload(chunk_hashes=("chunk-0", "chunk-1")),
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["source"]["id"], int)
    assert body["source"] == {
        "id": 1,
        "core_document_id": 1,
        "r2_object_key": "documents/1.pdf",
        "content_hash": "source-1",
        "status": "pending",
        "embedding_model": MODEL_A,
        "embedding_dim": 768,
        "metadata": {"topic": "graphs"},
    }
    assert [chunk["id"] for chunk in body["chunks"]] == [1, 2]
    assert {chunk["source_id"] for chunk in body["chunks"]} == {1}
    assert all("embedding" not in chunk for chunk in body["chunks"])


@pytest.mark.anyio
async def test_search_returns_only_committed_result_fields(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/knowledge-sources", json=_source_payload())

    response = await client.post(
        "/api/v1/knowledge-chunks/search", json=_search_payload(top_k=1)
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "chunk_id": 1,
            "source_id": 1,
            "page": 1,
            "text": "chunk 0 for model-a",
            "score": pytest.approx(1.0),
        }
    ]


@pytest.mark.anyio
async def test_search_returns_empty_list(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/knowledge-chunks/search", json=_search_payload()
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.anyio
async def test_search_isolates_embedding_models(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/knowledge-sources",
        json=_source_payload(core_document_id=1, model=MODEL_A),
    )
    await client.post(
        "/api/v1/knowledge-sources",
        json=_source_payload(core_document_id=2, model=MODEL_B),
    )

    response = await client.post(
        "/api/v1/knowledge-chunks/search",
        json=_search_payload(model=MODEL_B),
    )

    assert [result["text"] for result in response.json()] == ["chunk 0 for model-b"]


@pytest.mark.anyio
async def test_service_vector_validation_uses_stable_error_shape(
    client: AsyncClient,
) -> None:
    payload = _search_payload()
    payload["embedding"] = [1.0, 0.0]

    response = await client.post("/api/v1/knowledge-chunks/search", json=payload)

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "vector_validation_error",
            "message": "query embedding must contain exactly 768 values",
        }
    }


@pytest.mark.anyio
async def test_request_structure_validation_keeps_fastapi_error_shape(
    client: AsyncClient,
) -> None:
    payload = _search_payload()
    payload["embedding"] = ["not-a-number"]

    response = await client.post("/api/v1/knowledge-chunks/search", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.anyio
async def test_boolean_vector_value_is_a_request_structure_error(
    client: AsyncClient,
) -> None:
    payload = _search_payload()
    payload["embedding"] = [True, *(0.0 for _ in range(767))]

    response = await client.post("/api/v1/knowledge-chunks/search", json=payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


@pytest.mark.anyio
@pytest.mark.parametrize("top_k", [0, 101])
async def test_invalid_top_k_returns_domain_validation_error(
    client: AsyncClient, top_k: int
) -> None:
    response = await client.post(
        "/api/v1/knowledge-chunks/search",
        json=_search_payload(top_k=top_k),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "vector_validation_error"


@pytest.mark.anyio
async def test_duplicate_source_returns_conflict(client: AsyncClient) -> None:
    payload = _source_payload()
    assert (
        await client.post("/api/v1/knowledge-sources", json=payload)
    ).status_code == 201

    response = await client.post("/api/v1/knowledge-sources", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "duplicate_knowledge_source",
        "message": "knowledge source already exists",
    }


@pytest.mark.anyio
async def test_duplicate_chunks_are_atomic_and_return_conflict(
    client: AsyncClient,
) -> None:
    duplicate = _source_payload(chunk_hashes=("same-hash", "same-hash"))

    response = await client.post("/api/v1/knowledge-sources", json=duplicate)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "duplicate_knowledge_chunk"

    created = await client.post("/api/v1/knowledge-sources", json=_source_payload())
    assert created.status_code == 201
    assert created.json()["source"]["id"] == 1
    assert created.json()["chunks"][0]["id"] == 1


class _FailingRepository:
    def __init__(self, error_type: type[VectorRepositoryError]) -> None:
        self._error_type = error_type

    def create_source_with_chunks(
        self,
        source: NewKnowledgeSource,
        chunks: tuple[NewKnowledgeChunk, ...],
    ) -> SourceCreationResult:
        raise self._error_type("private adapter detail")

    def search(
        self,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> list[ChunkSearchResult]:
        raise self._error_type("private adapter detail")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/v1/knowledge-sources", _source_payload()),
        ("/api/v1/knowledge-chunks/search", _search_payload()),
    ],
)
async def test_repository_unavailable_returns_safe_503(
    path: str, payload: dict[str, object]
) -> None:
    application = ai_main.create_app(
        repository=_FailingRepository(VectorRepositoryUnavailableError)
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(path, json=payload)

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "vector_repository_unavailable",
            "message": "vector repository is unavailable",
        }
    }
    assert "private adapter detail" not in response.text


@pytest.mark.anyio
async def test_other_repository_errors_remain_safe_internal_errors() -> None:
    application = ai_main.create_app(
        repository=_FailingRepository(VectorRepositoryError)
    )
    transport = ASGITransport(app=application, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/knowledge-chunks/search", json=_search_payload()
        )

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert "private adapter detail" not in response.text


@pytest.mark.anyio
async def test_openapi_registers_vector_endpoints_and_schemas(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert set(document["paths"]["/api/v1/knowledge-sources"]) == {"post"}
    assert set(document["paths"]["/api/v1/knowledge-chunks/search"]) == {"post"}
    schemas = document["components"]["schemas"]
    assert "KnowledgeSourceCreate" in schemas
    assert "KnowledgeSourceCreationResponse" in schemas
    assert "ChunkSearchRequest" in schemas
    assert "ChunkSearchResultResponse" in schemas
    assert "embedding" not in schemas["KnowledgeChunkResponse"]["properties"]


def test_import_and_test_app_construction_need_no_credentials(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    reloaded = importlib.reload(ai_main)
    application = reloaded.create_app(repository=InMemoryVectorRepository())

    assert application.state.vector_service is not None


@pytest.mark.parametrize(
    "database_url",
    ["postgresql://user:password@localhost/greader", "sqlite:///greader.db"],
)
def test_production_factory_requires_psycopg_driver(
    monkeypatch, database_url: str
) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)

    with pytest.raises(RuntimeError, match=r"postgresql\+psycopg://"):
        ai_main.create_production_app()


def test_production_factory_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        ai_main.create_production_app()


def test_production_factory_selects_postgres_without_connecting(monkeypatch) -> None:
    repository = InMemoryVectorRepository()
    engine = object()
    create_engine_calls: list[tuple[object, bool]] = []

    def fake_create_engine(url: object, *, echo: bool) -> object:
        create_engine_calls.append((url, echo))
        return engine

    def fake_postgres_repository(session_factory):
        assert callable(session_factory)
        return repository

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:password@localhost/greader",
    )
    monkeypatch.setattr(postgres_adapter, "create_engine", fake_create_engine)
    monkeypatch.setattr(
        postgres_adapter, "PostgresVectorRepository", fake_postgres_repository
    )

    application = ai_main.create_production_app()

    assert application.state.vector_service is not None
    assert len(create_engine_calls) == 1
    assert create_engine_calls[0][0].drivername == "postgresql+psycopg"
    assert create_engine_calls[0][1] is False
