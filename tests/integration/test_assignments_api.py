"""HTTP integration tests for the Assignment API."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import create_app


@pytest.fixture()
async def client() -> AsyncClient:
    """Yield an isolated async client for one test."""
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as test_client:
        yield test_client


def assignment_payload() -> dict[str, object]:
    """Return a valid assignment request body."""
    return {
        "title": "Assignment CORE-04 Test",
        "problem_statement": "Test problem statement",
        "difficulty": "medium",
        "metadata": {},
    }


@pytest.mark.anyio
async def test_create_assignment(client: AsyncClient) -> None:
    response = await client.post("/api/v1/assignments", json=assignment_payload())

    assert response.status_code == 201
    assert response.json()["title"] == "Assignment CORE-04 Test"


@pytest.mark.anyio
async def test_create_assignment_validates_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/assignments",
        json={"title": "", "problem_statement": "", "difficulty": "invalid"},
    )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_list_assignments(client: AsyncClient) -> None:
    created = await client.post("/api/v1/assignments", json=assignment_payload())

    response = await client.get("/api/v1/assignments")

    assert response.status_code == 200
    assert response.json() == [created.json()]


@pytest.mark.anyio
async def test_get_assignment(client: AsyncClient) -> None:
    created = await client.post("/api/v1/assignments", json=assignment_payload())
    assignment_id = created.json()["id"]

    response = await client.get(f"/api/v1/assignments/{assignment_id}")

    assert response.status_code == 200
    assert response.json() == created.json()


@pytest.mark.anyio
async def test_get_missing_assignment_returns_stable_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/assignments/99999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": {
            "code": "assignment_not_found",
            "message": "Assignment not found",
        }
    }


@pytest.mark.anyio
async def test_update_assignment(client: AsyncClient) -> None:
    created = await client.post("/api/v1/assignments", json=assignment_payload())
    assignment_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/assignments/{assignment_id}",
        json={
            "title": "Updated CORE-04 Title",
            "problem_statement": "Updated statement",
            "difficulty": "hard",
            "metadata": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated CORE-04 Title"


@pytest.mark.anyio
async def test_update_missing_assignment_returns_stable_error(
    client: AsyncClient,
) -> None:
    response = await client.put(
        "/api/v1/assignments/99999",
        json={"title": "X", "problem_statement": "Y", "difficulty": "easy"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "assignment_not_found"


@pytest.mark.anyio
async def test_delete_assignment(client: AsyncClient) -> None:
    created = await client.post("/api/v1/assignments", json=assignment_payload())
    assignment_id = created.json()["id"]

    response = await client.delete(f"/api/v1/assignments/{assignment_id}")

    assert response.status_code == 204


@pytest.mark.anyio
async def test_delete_missing_assignment_returns_stable_error(
    client: AsyncClient,
) -> None:
    response = await client.delete("/api/v1/assignments/99999")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "assignment_not_found"
