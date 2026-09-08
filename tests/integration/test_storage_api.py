"""HTTP integration tests for the R2 file-upload endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.database.storage import MAX_UPLOAD_SIZE_BYTES, get_r2_client
from greader.main import create_app


class FakeR2Client:
    """Stub in place of the boto3 client — never touches real R2."""

    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []

    def upload_file(self, local_path: str, bucket: str, key: str) -> None:
        self.uploads.append((local_path, bucket, key))


@pytest.fixture()
async def fake_r2_client():
    return FakeR2Client()


@pytest.fixture()
async def client(fake_r2_client: FakeR2Client):
    application = create_app()
    application.dependency_overrides[get_r2_client] = lambda: fake_r2_client
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_upload_stores_file_and_returns_bucket_key(
    client: AsyncClient, fake_r2_client: FakeR2Client
) -> None:
    response = await client.post(
        "/api/v1/uploads",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bucket"]
    assert body["key"].startswith("uploads/")
    assert body["key"].endswith("-notes.txt")
    assert len(fake_r2_client.uploads) == 1


@pytest.mark.anyio
async def test_upload_rejects_file_over_size_limit(client: AsyncClient) -> None:
    oversized = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1)

    response = await client.post(
        "/api/v1/uploads",
        files={"file": ("big.bin", oversized, "application/octet-stream")},
    )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_openapi_describes_upload_operation(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]["/api/v1/uploads"]) == {"post"}
