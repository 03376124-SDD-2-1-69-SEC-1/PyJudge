"""API integration tests for the knowledge document upload endpoint."""

import pytest
from httpx import AsyncClient

from questly.core.auth.models import Role
from questly.core.uploads.models import DocumentStatus
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user
from tests.fakes.uploads import (
    FakeDocumentIngestor,
    FakeKnowledgeDocumentRepository,
    FakeObjectStorage,
)
from tests.integration.forms import asgi_client, log_in

MAX_UPLOAD_SIZE_BYTES = 64
TEACHER = "somchai.p@kmitl.ac.th"
STUDENT = "66010001@kmitl.ac.th"
LECTURE = {"file": ("lecture.pdf", b"%PDF-1.4 fake", "application/pdf")}


class Campus:
    """An app with one Instructor and one Student, and the fakes behind it."""

    def __init__(self, *, ingestion_fails: bool = False) -> None:
        users = FakeAuthRepository()
        self.teacher = seed_user(
            users, email=TEACHER, full_name="Somchai", role=Role.INSTRUCTOR
        )
        seed_user(users, email=STUDENT, full_name="Nattapong")
        self.storage = FakeObjectStorage()
        self.documents = FakeKnowledgeDocumentRepository()
        self.ingestor = FakeDocumentIngestor(page_count=5, fails=ingestion_fails)
        self.app = build_app(
            auth_repository=users,
            object_storage=self.storage,
            knowledge_document_repository=self.documents,
            document_ingestor=self.ingestor,
            max_upload_size_bytes=MAX_UPLOAD_SIZE_BYTES,
        )

    async def client(self, email: str | None = None) -> AsyncClient:
        client = asgi_client(self.app)
        if email is not None:
            await log_in(client, email, DEFAULT_PASSWORD)
        return client


@pytest.mark.anyio
async def test_instructor_upload_is_stored_then_ingested_in_the_background() -> None:
    campus = Campus()
    client = await campus.client(TEACHER)

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["filename"] == "lecture.pdf"
    assert body["object_key"].startswith("uploads/")
    assert body["object_key"].endswith("-lecture.pdf")
    assert body["status"] == "uploaded"
    assert list(campus.storage.objects) == [body["object_key"]]
    stored = campus.documents.get(body["id"])
    assert stored.uploaded_by == campus.teacher.id
    assert stored.status is DocumentStatus.READY
    assert stored.page_count == 5
    assert (await client.get(f"/api/v1/uploads/{body['id']}")).json()["status"] == (
        "ready"
    )
    assert campus.ingestor.ingested[0][1] == b"%PDF-1.4 fake"


@pytest.mark.anyio
async def test_a_failed_ingestion_leaves_the_document_failed() -> None:
    campus = Campus(ingestion_fails=True)
    client = await campus.client(TEACHER)

    created = await client.post("/api/v1/uploads", files=LECTURE)

    assert created.status_code == 201
    response = await client.get(f"/api/v1/uploads/{created.json()['id']}")
    assert response.json()["status"] == "failed"


@pytest.mark.anyio
async def test_uploading_the_same_bytes_again_does_not_ingest_twice() -> None:
    campus = Campus()
    client = await campus.client(TEACHER)

    first = await client.post("/api/v1/uploads", files=LECTURE)
    second = await client.post("/api/v1/uploads", files=LECTURE)

    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert len(campus.ingestor.ingested) == 1
    assert len(campus.storage.objects) == 1


@pytest.mark.anyio
async def test_a_student_cannot_upload() -> None:
    campus = Campus()
    client = await campus.client(STUDENT)

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "forbidden"
    assert campus.storage.objects == {}
    assert campus.ingestor.ingested == []


@pytest.mark.anyio
async def test_upload_needs_a_login() -> None:
    campus = Campus()
    client = await campus.client()

    response = await client.post("/api/v1/uploads", files=LECTURE)

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "not_authenticated"
    assert campus.storage.objects == {}


@pytest.mark.anyio
async def test_oversized_upload_is_rejected_and_not_ingested() -> None:
    campus = Campus()
    client = await campus.client(TEACHER)

    response = await client.post(
        "/api/v1/uploads",
        files={"file": ("big.pdf", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1), "x/y")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "upload_too_large"
    assert campus.ingestor.ingested == []


@pytest.mark.anyio
async def test_empty_upload_is_rejected() -> None:
    campus = Campus()
    client = await campus.client(TEACHER)

    response = await client.post(
        "/api/v1/uploads", files={"file": ("empty.pdf", b"", "application/pdf")}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "empty_upload"


@pytest.mark.anyio
async def test_unknown_document_returns_404() -> None:
    client = await Campus().client(TEACHER)

    response = await client.get("/api/v1/uploads/999999")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "knowledge_document_not_found"
