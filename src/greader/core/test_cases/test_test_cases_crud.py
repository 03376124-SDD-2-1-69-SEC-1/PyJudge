from fastapi import status
from fastapi.testclient import TestClient

from greader.main import app

client = TestClient(app)


def test_test_cases_crud_endpoints():
    # 1. Create Assignment first to attach test cases
    assign_res = client.post(
        "/api/v1/assignments",
        json={
            "title": "Assignment for TestCase Test",
            "problem_statement": "Problem statement",
            "difficulty": "easy",
            "metadata": {},
        },
    )
    assert assign_res.status_code == status.HTTP_201_CREATED
    assign_id = assign_res.json()["id"]

    # 2. Create Test Case (201)
    tc_res = client.post(
        f"/api/v1/assignments/{assign_id}/test-cases",
        json={
            "input_data": "1 2",
            "expected_output": "3",
            "is_hidden": False,
            "order_index": 1,
        },
    )
    assert tc_res.status_code == status.HTTP_201_CREATED
    tc_data = tc_res.json()
    assert tc_data["input_data"] == "1 2"
    tc_id = tc_data["id"]

    # 3. List Test Cases for Assignment (200)
    list_res = client.get(f"/api/v1/assignments/{assign_id}/test-cases")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) > 0

    # 4. Get Test Case Detail (200)
    detail_res = client.get(f"/api/v1/assignments/{assign_id}/test-cases/{tc_id}")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.json()["id"] == tc_id

    # 5. Update Test Case (200)
    update_res = client.put(
        f"/api/v1/assignments/{assign_id}/test-cases/{tc_id}",
        json={
            "input_data": "2 3",
            "expected_output": "5",
            "is_hidden": True,
            "order_index": 2,
        },
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["expected_output"] == "5"

    # 6. Delete Test Case (204)
    del_res = client.delete(f"/api/v1/assignments/{assign_id}/test-cases/{tc_id}")
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # 7. Get Non-existent Test Case (404)
    assert (
        client.get(f"/api/v1/assignments/{assign_id}/test-cases/99999").status_code
        == status.HTTP_404_NOT_FOUND
    )
