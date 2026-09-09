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

    # 4. Delete Assignment (204 / 404)
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_204_NO_CONTENT
    )
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_404_NOT_FOUND
    )
