"""HTTP integration tests for the R2 file-upload endpoint."""

from unittest.mock import Mock

import pytest
from httpx import ASGITransport, AsyncClient

from greader.database.storage import MAX_UPLOAD_SIZE_BYTES, R2Storage, get_r2_storage
from greader.main import create_app


class FakeR2Client:
    """Stub in place of the boto3 client — never touches real R2."""

    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []
        self.checked_buckets: list[str] = []

    def head_bucket(self, *, Bucket: str) -> None:
        self.checked_buckets.append(Bucket)

    def upload_file(self, local_path: str, bucket: str, key: str) -> None:
        self.uploads.append((local_path, bucket, key))


@pytest.fixture()
async def fake_r2_client():
    return FakeR2Client()


@pytest.fixture()
def no_r2_credentials(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    for name in (
        "R2_ENDPOINT_URL",
        "R2_BUCKET_NAME",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    factory = Mock(side_effect=AssertionError("real R2 client constructed"))
    monkeypatch.setattr("greader.database.storage.boto3.client", factory)
    yield
    factory.assert_not_called()


@pytest.fixture()
async def client(fake_r2_client: FakeR2Client, no_r2_credentials):
    application = create_app()
    application.dependency_overrides[get_r2_storage] = lambda: R2Storage(
        client=fake_r2_client, bucket="injected-test-bucket"
    )
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
    assert body["bucket"] == "injected-test-bucket"
    assert body["key"].startswith("uploads/")
    assert body["key"].endswith("-notes.txt")
    assert len(fake_r2_client.uploads) == 1
    assert fake_r2_client.uploads[0][1:] == (body["bucket"], body["key"])


@pytest.mark.anyio
async def test_health_uses_injected_bucket_without_credentials(client, fake_r2_client):
    response = await client.get("/health/r2")
    assert response.status_code == 200
    assert response.json() == {"connected": True, "bucket": "injected-test-bucket"}
    assert fake_r2_client.checked_buckets == ["injected-test-bucket"]


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
