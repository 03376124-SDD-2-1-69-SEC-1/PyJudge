from fastapi import status
from fastapi.testclient import TestClient

from greader.main import app

client = TestClient(app)


def test_assignments_crud_endpoints():
    # 1. Validation Error Check (422)
    res = client.post(
        "/api/v1/assignments",
        json={"title": "", "problem_statement": "", "difficulty": "invalid"},
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # 2. Create Assignment (201)
    res = client.post(
        "/api/v1/assignments",
        json={
            "title": "Assignment CORE-04 Test",
            "problem_statement": "Test problem statement",
            "difficulty": "medium",
            "metadata": {},
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["title"] == "Assignment CORE-04 Test"
    assign_id = data["id"]

    # 3. List Assignments (200)
    res_list = client.get("/api/v1/assignments")
    assert res_list.status_code == status.HTTP_200_OK
    assert len(res_list.json()) > 0

    # 4. Get Assignment Detail (200)
    res_detail = client.get(f"/api/v1/assignments/{assign_id}")
    assert res_detail.status_code == status.HTTP_200_OK
    assert res_detail.json()["id"] == assign_id

    # 5. Get Non-existent Assignment (404)
    assert (
        client.get("/api/v1/assignments/99999").status_code == status.HTTP_404_NOT_FOUND
    )

    # 6. Update Assignment (200)
    res_update = client.put(
        f"/api/v1/assignments/{assign_id}",
        json={
            "title": "Updated CORE-04 Title",
            "problem_statement": "Updated statement",
            "difficulty": "hard",
            "metadata": {},
        },
    )
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["title"] == "Updated CORE-04 Title"

    # 7. Update Non-existent Assignment (404)
    assert (
        client.put(
            "/api/v1/assignments/99999",
            json={
                "title": "X",
                "problem_statement": "Y",
                "difficulty": "easy",
            },
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    # 8. Delete Assignment (204)
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_204_NO_CONTENT
    )

    # 9. Delete Non-existent Assignment (404)
    assert (
        client.delete(f"/api/v1/assignments/{assign_id}").status_code
        == status.HTTP_404_NOT_FOUND
    )


def test_update_assignment_without_metadata():
    # 1. Create assignment
    res = client.post(
        "/api/v1/assignments",
        json={
            "title": "HW1 Bug Fix Test",
            "problem_statement": "Test problem",
            "difficulty": "easy",
            "metadata": {"initial": "value"},
        },
    )
    assert res.status_code == status.HTTP_201_CREATED
    assign_id = res.json()["id"]

    # 2. Update without including 'metadata' in payload (Should return 200 OK)
    res_update = client.put(
        f"/api/v1/assignments/{assign_id}",
        json={
            "title": "HW1 Updated",
            "problem_statement": "Updated problem",
            "difficulty": "medium",
        },
    )
    assert res_update.status_code == status.HTTP_200_OK
    assert res_update.json()["title"] == "HW1 Updated"
