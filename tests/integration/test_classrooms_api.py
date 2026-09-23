"""HTTP tests for /api/v1/classrooms, including 401/403/404."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.core.auth.models import Role
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user

NEW_CLASSROOM = {
    "course_code": "01076001",
    "course_name": "Programming I",
    "section": "1",
    "semester": "1/2569",
}


class Campus:
    """One app with seeded accounts; `client_for(email)` logs in fresh."""

    def __init__(self) -> None:
        self.users = FakeAuthRepository()
        for email, name, role in [
            ("somchai.p@kmitl.ac.th", "Somchai Prasert", Role.INSTRUCTOR),
            ("warunee.k@kmitl.ac.th", "Warunee Kaew", Role.INSTRUCTOR),
            ("66010001@kmitl.ac.th", "Nattapong Suwan", Role.STUDENT),
            ("66010002@kmitl.ac.th", "Pimchanok Wong", Role.STUDENT),
            ("admin@kmitl.ac.th", "Admin", Role.ADMIN),
        ]:
            seed_user(self.users, email=email, full_name=name, role=role)
        self.app = build_app(auth_repository=self.users)

    async def client_for(self, email: str) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://testserver"
        )
        response = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": DEFAULT_PASSWORD}
        )
        assert response.status_code == 200
        return client


TEACHER = "somchai.p@kmitl.ac.th"
OTHER_TEACHER = "warunee.k@kmitl.ac.th"
STUDENT = "66010001@kmitl.ac.th"
OTHER_STUDENT = "66010002@kmitl.ac.th"
ADMIN = "admin@kmitl.ac.th"


async def _classroom_with_member(campus: Campus) -> dict:
    teacher = await campus.client_for(TEACHER)
    created = (await teacher.post("/api/v1/classrooms", json=NEW_CLASSROOM)).json()
    student = await campus.client_for(STUDENT)
    await student.post(
        "/api/v1/classrooms/join", json={"join_code": created["join_code"]}
    )
    return created


@pytest.mark.anyio
async def test_requires_a_session() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_app()), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/classrooms")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_then_list_as_instructor() -> None:
    campus = Campus()
    teacher = await campus.client_for(TEACHER)

    created = await teacher.post("/api/v1/classrooms", json=NEW_CLASSROOM)
    picker = await teacher.get("/api/v1/classrooms")

    assert created.status_code == 201
    assert len(created.json()["join_code"]) == 6
    assert picker.json()["variant"] == "instructor"
    assert picker.json()["instructor_cards"][0]["student_count"] == 0


@pytest.mark.anyio
async def test_student_cannot_create() -> None:
    student = await Campus().client_for(STUDENT)

    response = await student.post("/api/v1/classrooms", json=NEW_CLASSROOM)

    assert response.status_code == 403


@pytest.mark.anyio
async def test_join_then_student_picker_and_hidden_join_code() -> None:
    campus = Campus()
    created = await _classroom_with_member(campus)
    student = await campus.client_for(STUDENT)

    picker = await student.get("/api/v1/classrooms")
    detail = await student.get(f"/api/v1/classrooms/{created['id']}")

    assert picker.json()["variant"] == "student"
    assert picker.json()["student_cards"][0]["instructor_name"] == "Somchai Prasert"
    assert detail.status_code == 200
    assert detail.json()["join_code"] is None


@pytest.mark.anyio
async def test_join_with_an_invalid_code_is_422() -> None:
    student = await Campus().client_for(STUDENT)

    response = await student.post(
        "/api/v1/classrooms/join", json={"join_code": "ZZZZZZ"}
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_join_code"


@pytest.mark.anyio
async def test_outsiders_get_404_and_members_get_403() -> None:
    campus = Campus()
    created = await _classroom_with_member(campus)
    path = f"/api/v1/classrooms/{created['id']}"
    member = await campus.client_for(STUDENT)
    outsider_student = await campus.client_for(OTHER_STUDENT)
    outsider_teacher = await campus.client_for(OTHER_TEACHER)

    assert (await outsider_student.get(path)).status_code == 404
    assert (await outsider_teacher.get(path)).status_code == 404
    assert (await member.get(f"{path}/members")).status_code == 403
    assert (await member.patch(path, json={"section": "9"})).status_code == 403
    assert (await member.post(f"{path}/archive")).status_code == 403


@pytest.mark.anyio
async def test_admin_has_no_picker() -> None:
    admin = await Campus().client_for(ADMIN)

    assert (await admin.get("/api/v1/classrooms")).status_code == 403


@pytest.mark.anyio
async def test_owner_manages_settings_code_members_and_archive() -> None:
    campus = Campus()
    created = await _classroom_with_member(campus)
    path = f"/api/v1/classrooms/{created['id']}"
    teacher = await campus.client_for(TEACHER)

    patched = await teacher.patch(path, json={"course_name": "Prog I"})
    regenerated = await teacher.post(f"{path}/join-code")
    disabled = await teacher.delete(f"{path}/join-code")
    members = await teacher.get(f"{path}/members")
    member_id = members.json()[0]["user_id"]
    removed = await teacher.delete(f"{path}/members/{member_id}")
    removed_again = await teacher.delete(f"{path}/members/{member_id}")
    archived = await teacher.post(f"{path}/archive")
    unarchived = await teacher.post(f"{path}/unarchive")

    assert patched.json()["course_name"] == "Prog I"
    assert patched.json()["section"] == "1"
    assert regenerated.json()["join_code"] != created["join_code"]
    assert disabled.json()["join_code"] is None
    assert members.json()[0]["student_number"] == "66010001"
    assert removed.status_code == 204
    assert removed_again.status_code == 404
    assert archived.json()["archived"] is True
    assert unarchived.json()["archived"] is False


@pytest.mark.anyio
async def test_patch_rejects_null_and_blank() -> None:
    campus = Campus()
    teacher = await campus.client_for(TEACHER)
    created = (await teacher.post("/api/v1/classrooms", json=NEW_CLASSROOM)).json()

    response = await teacher.patch(
        f"/api/v1/classrooms/{created['id']}", json={"course_name": None}
    )

    assert response.status_code == 422
