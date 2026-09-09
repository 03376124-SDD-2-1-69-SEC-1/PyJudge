"""HTTP integration tests for the TestCase sub-resource under an Assignment."""

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


async def _create_assignment(client: AsyncClient) -> int:
    """Create an Assignment and return its id."""
    response = await client.post(
        "/api/v1/assignments",
        json={
            "title": "Assignment for TestCase tests",
            "problem_statement": "Problem statement",
            "difficulty": "easy",
            "metadata": {},
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def valid_test_case_payload() -> dict[str, object]:
    """Return a valid test case request body."""
    return {
        "input_data": "1 2",
        "expected_output": "3",
        "is_hidden": False,
        "order_index": 1,
    }


@pytest.mark.anyio
async def test_create_test_case(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)

    response = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["input_data"] == "1 2"
    assert body["assignment_id"] == assignment_id


@pytest.mark.anyio
async def test_create_test_case_on_missing_assignment_returns_stable_error(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/assignments/99999/test-cases", json=valid_test_case_payload()
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "assignment_not_found"


@pytest.mark.anyio
async def test_list_test_cases(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)
    await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )

    response = await client.get(f"/api/v1/assignments/{assignment_id}/test-cases")

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.anyio
async def test_get_test_case(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)
    created = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )
    test_case_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/assignments/{assignment_id}/test-cases/{test_case_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_case_id


@pytest.mark.anyio
async def test_get_missing_test_case_returns_stable_error(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)

    response = await client.get(f"/api/v1/assignments/{assignment_id}/test-cases/99999")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "test_case_not_found"


@pytest.mark.anyio
async def test_update_test_case(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)
    created = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )
    test_case_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/assignments/{assignment_id}/test-cases/{test_case_id}",
        json={
            "input_data": "2 3",
            "expected_output": "5",
            "is_hidden": True,
            "order_index": 2,
        },
    )

    assert response.status_code == 200
    assert response.json()["expected_output"] == "5"


@pytest.mark.anyio
async def test_update_test_case_title_only_preserves_other_fields(
    client: AsyncClient,
) -> None:
    assignment_id = await _create_assignment(client)
    created = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )
    test_case_id = created.json()["id"]

    response = await client.put(
        f"/api/v1/assignments/{assignment_id}/test-cases/{test_case_id}",
        json={"is_hidden": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_hidden"] is True
    assert body["input_data"] == "1 2"
    assert body["expected_output"] == "3"


@pytest.mark.anyio
async def test_delete_test_case(client: AsyncClient) -> None:
    assignment_id = await _create_assignment(client)
    created = await client.post(
        f"/api/v1/assignments/{assignment_id}/test-cases",
        json=valid_test_case_payload(),
    )
    test_case_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/assignments/{assignment_id}/test-cases/{test_case_id}"
    )

    assert response.status_code == 204
    listed = await client.get(f"/api/v1/assignments/{assignment_id}/test-cases")
    assert listed.json() == []


@pytest.mark.anyio
async def test_delete_missing_test_case_returns_stable_error(
    client: AsyncClient,
) -> None:
    assignment_id = await _create_assignment(client)

    response = await client.delete(
        f"/api/v1/assignments/{assignment_id}/test-cases/99999"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "test_case_not_found"
