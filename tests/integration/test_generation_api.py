"""HTTP integration tests for the mock generation endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import create_app


@pytest.fixture()
async def client():
    application = create_app()
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
    assert body["draft"]["title"]
    assert body["draft"]["test_cases"]
    assert body["citations"]


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
async def test_openapi_describes_generation_operation(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]["/api/v1/generations"]) == {"post"}
