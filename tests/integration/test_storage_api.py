"""HTTP integration tests for the knowledge document upload endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.fakes.app import build_app
from tests.fakes.uploads import FakeKnowledgeDocumentRepository, FakeObjectStorage

MAX_UPLOAD_SIZE_BYTES = 64


@pytest.fixture()
async def storage() -> FakeObjectStorage:
    return FakeObjectStorage()


@pytest.fixture()
async def documents() -> FakeKnowledgeDocumentRepository:
    return FakeKnowledgeDocumentRepository()


@pytest.fixture()
async def client(
    storage: FakeObjectStorage, documents: FakeKnowledgeDocumentRepository
):
    application = build_app(
        object_storage=storage,
        knowledge_document_repository=documents,
        max_upload_size_bytes=MAX_UPLOAD_SIZE_BYTES,
    )
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_upload_stores_the_object_and_indexes_a_document(
    client: AsyncClient, storage: FakeObjectStorage
) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["filename"] == "notes.txt"
    assert body["object_key"].startswith("uploads/")
    assert body["object_key"].endswith("-notes.txt")
    assert body["status"] == "uploaded"
    assert list(storage.objects) == [body["object_key"]]


@pytest.mark.anyio
async def test_uploaded_document_is_readable_by_id(client: AsyncClient) -> None:
    """A citation's document_id resolves to a filename through Core (CORE-09)."""
    created = await client.post(
        "/api/v1/uploads",
        files={"file": ("lecture.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    document_id = created.json()["id"]

    response = await client.get(f"/api/v1/uploads/{document_id}")

    assert response.status_code == 200
    assert response.json()["filename"] == "lecture.pdf"


@pytest.mark.anyio
async def test_unknown_document_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/uploads/999999")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "knowledge_document_not_found"


@pytest.mark.anyio
async def test_upload_rejects_file_over_size_limit(
    client: AsyncClient, storage: FakeObjectStorage
) -> None:
    oversized = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)

    response = await client.post(
        "/api/v1/uploads",
        files={"file": ("big.bin", oversized, "application/octet-stream")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "upload_too_large"
    assert storage.objects == {}


@pytest.mark.anyio
async def test_openapi_describes_upload_operations(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths["/api/v1/uploads"]) == {"post"}
    assert set(paths["/api/v1/uploads/{document_id}"]) == {"get"}
