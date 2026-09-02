"""HTTP integration tests for the Topic reference API."""

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
async def test_topic_crud_lifecycle(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/topics",
        json={"name": "Graphs", "description": "Network problems"},
    )

    assert created.status_code == 201
    topic = created.json()
    assert topic["name"] == "Graphs"

    listed = await client.get("/api/v1/topics")
    assert listed.status_code == 200
    assert listed.json() == [topic]

    updated = await client.put(
        f"/api/v1/topics/{topic['id']}",
        json={"name": "Trees", "description": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Trees"

    deleted = await client.delete(f"/api/v1/topics/{topic['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/topics/{topic['id']}")).status_code == 404


@pytest.mark.anyio
async def test_topic_duplicate_name_returns_stable_error_code(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/topics", json={"name": "Graphs"})

    response = await client.post("/api/v1/topics", json={"name": " graphs "})

    assert response.status_code == 409
    assert response.json() == {"detail": {"code": "topic_name_conflict"}}


@pytest.mark.anyio
async def test_openapi_describes_every_topic_operation(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]["/api/v1/topics"]) == {"get", "post"}
    assert set(response.json()["paths"]["/api/v1/topics/{topic_id}"]) == {
        "get",
        "put",
        "delete",
    }
