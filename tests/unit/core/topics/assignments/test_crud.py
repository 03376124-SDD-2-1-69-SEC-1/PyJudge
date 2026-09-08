from fastapi import status
from fastapi.testclient import TestClient

from greader.main import app

client = TestClient(app)


def test_assignment_crud_flow():
    # 1. Validation Error (422)
    res = client.post(
        "/api/v1/assignments",
        json={"title": "", "problem_statement": "", "difficulty": "invalid"},
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 2. Create Assignment (201)
    res = client.post(
        "/api/v1/assignments",
        json={
            "title": "HW1",
            "problem_statement": "Do X",
            "difficulty": "easy",
            "metadata": {},
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    assign_id = res.json()["id"]

    # 3. Get Assignment List & Detail (200 / 404)
    assert client.get("/api/v1/assignments").status_code == status.HTTP_200_OK
    assert (
        client.get(f"/api/v1/assignments/{assign_id}").status_code == status.HTTP_200_OK
    )
    assert (
        client.get("/api/v1/assignments/999").status_code == status.HTTP_404_NOT_FOUND
    )

    # 4. Create Test Case (201)
    tc_res = client.post(
        f"/api/v1/assignments/{assign_id}/test-cases",
        json={
            "input_data": "1",
            "expected_output": "2",
            "is_hidden": False,
            "weight": 1.0,
        },
    )
    assert tc_res.status_code == status.HTTP_201_CREATED
    tc_id = tc_res.json()["id"]

    # 5. Update & Delete Test Case
    assert (
        client.put(
            f"/api/v1/assignments/{assign_id}/test-cases/{tc_id}",
            json={"input_data": "2", "expected_output": "3"},
        ).status_code
        == status.HTTP_200_OK
    )
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}/test-cases/{tc_id}").status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}/test-cases/999").status_code
        == status.HTTP_404_NOT_FOUND
    )

    # 6. Delete Assignment
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_404_NOT_FOUND
    )
