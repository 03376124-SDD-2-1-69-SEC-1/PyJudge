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
async def test_topic_patch_updates_only_the_given_field(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/topics",
        json={"name": "Graphs", "description": "Network problems"},
    )
    topic = created.json()

    patched = await client.patch(
        f"/api/v1/topics/{topic['id']}",
        json={"name": "Trees"},
    )

    assert patched.status_code == 200
    assert patched.json()["name"] == "Trees"
    assert patched.json()["description"] == "Network problems"


@pytest.mark.anyio
async def test_topic_patch_empty_body_is_a_no_op(client: AsyncClient) -> None:
    created = await client.post("/api/v1/topics", json={"name": "Graphs"})
    topic = created.json()

    patched = await client.patch(f"/api/v1/topics/{topic['id']}", json={})

    assert patched.status_code == 200
    assert patched.json() == topic


@pytest.mark.anyio
async def test_topic_patch_unknown_id_returns_404(client: AsyncClient) -> None:
    response = await client.patch("/api/v1/topics/missing", json={"name": "Trees"})

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "topic_not_found"}}


@pytest.mark.anyio
async def test_topic_patch_duplicate_name_returns_409(client: AsyncClient) -> None:
    await client.post("/api/v1/topics", json={"name": "Graphs"})
    created = await client.post("/api/v1/topics", json={"name": "Trees"})
    topic = created.json()

    response = await client.patch(
        f"/api/v1/topics/{topic['id']}",
        json={"name": " graphs "},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": {"code": "topic_name_conflict"}}


@pytest.mark.anyio
async def test_topic_patch_blank_name_returns_422(client: AsyncClient) -> None:
    created = await client.post("/api/v1/topics", json={"name": "Graphs"})
    topic = created.json()

    response = await client.patch(
        f"/api/v1/topics/{topic['id']}",
        json={"name": "   "},
    )

    assert response.status_code == 422


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
        "patch",
        "delete",
    }
