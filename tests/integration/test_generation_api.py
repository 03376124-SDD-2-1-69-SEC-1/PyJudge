"""HTTP integration tests for the generation endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.fakes.app import build_app


@pytest.fixture()
async def client():
    application = build_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_generate_returns_draft_and_citations(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/generations",
        json={"prompt": "write a sorting assignment"},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["draft"]["title"]
    assert body["draft"]["test_cases"]
    assert body["citations"]
    assert body["review_status"] == "pending"


@pytest.mark.anyio
async def test_generate_accepts_optional_filters(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/generations",
        json={
            "prompt": "write a graph assignment",
            "filters": {"topic": "graphs", "difficulty": "medium"},
        },
    )

    assert response.status_code == 201


@pytest.mark.anyio
async def test_get_generation_round_trips_what_post_created(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/generations",
        json={"prompt": "write a sorting assignment"},
    )
    artifact_id = created.json()["id"]

    response = await client.get(f"/api/v1/generations/{artifact_id}")

    assert response.status_code == 200
    assert response.json() == created.json()


@pytest.mark.anyio
async def test_get_missing_generation_returns_stable_error(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/generations/99999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "generation_artifact_not_found",
            "message": "Generation artifact not found",
        }
    }


@pytest.mark.anyio
async def test_generate_reports_a_stable_error_when_the_client_fails() -> None:
    class FailingClient:
        def generate(self, request: object) -> object:
            raise RuntimeError("upstream is down")

    application = build_app(generation_client=FailingClient())
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as failing_client:
        response = await failing_client.post(
            "/api/v1/generations", json={"prompt": "write a sorting assignment"}
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "generation_failed",
            "message": "The generation client failed to produce a draft",
        }
    }


@pytest.mark.anyio
async def test_openapi_describes_generation_operations(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths["/api/v1/generations"]) == {"post"}
    assert set(paths["/api/v1/generations/{artifact_id}"]) == {"get"}
