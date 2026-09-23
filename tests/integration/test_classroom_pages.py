"""HTTP tests for C-01/C-02/C-03 and /classes/{id} (T-01, S-01) per role."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.core.auth.models import Role
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, seed_user

FORM = {
    "course_code": "01076001",
    "course_name": "Programming I",
    "section": "1",
    "semester": "1/2569",
}
TEACHER = "somchai.p@kmitl.ac.th"
OTHER_TEACHER = "warunee.k@kmitl.ac.th"
STUDENT = "66010001@kmitl.ac.th"
OTHER_STUDENT = "66010002@kmitl.ac.th"
ADMIN = "admin@kmitl.ac.th"


def _page(response) -> tuple[str, str]:
    """(page ID, tab or variant) from the root element's data attributes."""
    text = response.text.split("<main", 1)[1]

    def attribute(name: str) -> str:
        marker = f'{name}="'
        if marker not in text:
            return ""
        start = text.index(marker) + len(marker)
        return text[start : text.index('"', start)]

    return attribute("data-page"), attribute("data-tab") or attribute("data-variant")


class Campus:
    def __init__(self) -> None:
        users = FakeAuthRepository()
        for email, name, role in [
            (TEACHER, "Somchai Prasert", Role.INSTRUCTOR),
            (OTHER_TEACHER, "Warunee Kaew", Role.INSTRUCTOR),
            (STUDENT, "Nattapong Suwan", Role.STUDENT),
            (OTHER_STUDENT, "Pimchanok Wong", Role.STUDENT),
            (ADMIN, "Admin", Role.ADMIN),
        ]:
            seed_user(users, email=email, full_name=name, role=role)
        self.app = build_app(auth_repository=users)

    async def client_for(self, email: str) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://testserver"
        )
        await client.post("/login", data={"email": email, "password": DEFAULT_PASSWORD})
        return client

    async def classroom(self) -> tuple[int, str]:
        """Create a classroom as TEACHER with STUDENT joined; (id, join code)."""
        teacher = await self.client_for(TEACHER)
        created = await teacher.post("/classes", data=FORM)
        classroom_id = int(created.headers["location"].split("created=")[1])
        banner = await teacher.get(created.headers["location"])
        code = banner.text.split("<strong>")[1].split("</strong>")[0]
        student = await self.client_for(STUDENT)
        await student.post("/classes/join", data={"join_code": code})
        return classroom_id, code


@pytest.mark.anyio
async def test_anonymous_visitors_are_sent_to_login() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_app()), base_url="http://testserver"
    ) as client:
        response = await client.get("/classes")

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.anyio
async def test_picker_variant_per_role_and_empty_states() -> None:
    campus = Campus()
    teacher = await campus.client_for(TEACHER)
    student = await campus.client_for(STUDENT)

    teacher_page = await teacher.get("/classes")
    student_page = await student.get("/classes")

    assert _page(teacher_page) == ("C-01", "instructor")
    assert 'data-state="C-01a"' in teacher_page.text
    assert 'popover data-page="C-03"' in teacher_page.text
    assert _page(student_page) == ("C-01", "student")
    assert 'data-state="C-01b"' in student_page.text
    assert 'popover data-page="C-02"' in student_page.text
    assert "<script" not in teacher_page.text.lower()


@pytest.mark.anyio
async def test_admin_cannot_open_the_picker() -> None:
    admin = await Campus().client_for(ADMIN)

    assert (await admin.get("/classes")).status_code == 403


@pytest.mark.anyio
async def test_create_shows_c03a_with_the_join_code() -> None:
    campus = Campus()
    teacher = await campus.client_for(TEACHER)

    created = await teacher.post("/classes", data=FORM)
    banner = await teacher.get(created.headers["location"])

    assert created.status_code == 303
    assert 'data-state="C-03a"' in banner.text


@pytest.mark.anyio
async def test_join_lands_in_s01_and_a_bad_code_shows_c02a() -> None:
    campus = Campus()
    classroom_id, code = await campus.classroom()
    other = await campus.client_for(OTHER_STUDENT)

    joined = await other.post("/classes/join", data={"join_code": code.lower()})
    bad = await other.post("/classes/join", data={"join_code": "ZZZZZZ"})

    assert joined.headers["location"] == f"/classes/{classroom_id}"
    assert bad.status_code == 422
    assert 'data-state="C-02a"' in bad.text


@pytest.mark.anyio
@pytest.mark.parametrize("tab", ["problems", "summary", "members", "settings"])
async def test_instructor_sees_t01_tabs(tab: str) -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    teacher = await campus.client_for(TEACHER)

    response = await teacher.get(f"/classes/{classroom_id}?tab={tab}")

    assert response.status_code == 200
    assert _page(response) == ("T-01", tab)


@pytest.mark.anyio
@pytest.mark.parametrize("tab", ["problems", "summary"])
async def test_member_sees_s01_tabs(tab: str) -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    student = await campus.client_for(STUDENT)

    response = await student.get(f"/classes/{classroom_id}?tab={tab}")

    assert response.status_code == 200
    assert _page(response) == ("S-01", tab)


@pytest.mark.anyio
@pytest.mark.parametrize("tab", ["members", "settings"])
async def test_member_cannot_open_instructor_tabs(tab: str) -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    student = await campus.client_for(STUDENT)

    response = await student.get(f"/classes/{classroom_id}?tab={tab}")

    assert response.status_code == 403


@pytest.mark.anyio
async def test_unknown_tab_is_404() -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    teacher = await campus.client_for(TEACHER)

    response = await teacher.get(f"/classes/{classroom_id}?tab=nope")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_member_cannot_post_instructor_actions() -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    student = await campus.client_for(STUDENT)

    response = await student.post(f"/classes/{classroom_id}/archive")

    assert response.status_code == 403


@pytest.mark.anyio
@pytest.mark.parametrize("email", [OTHER_STUDENT, OTHER_TEACHER])
async def test_outsiders_get_404(email: str) -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    outsider = await campus.client_for(email)

    assert (await outsider.get(f"/classes/{classroom_id}")).status_code == 404
    assert (await outsider.post(f"/classes/{classroom_id}/archive")).status_code == 404


@pytest.mark.anyio
async def test_owner_settings_forms_redirect_back() -> None:
    campus = Campus()
    classroom_id, code = await campus.classroom()
    teacher = await campus.client_for(TEACHER)

    saved = await teacher.post(
        f"/classes/{classroom_id}/settings", data={**FORM, "course_name": "Prog I"}
    )
    regenerated = await teacher.post(f"/classes/{classroom_id}/join-code/regenerate")
    settings = await teacher.get(f"/classes/{classroom_id}?tab=settings")

    assert saved.headers["location"] == f"/classes/{classroom_id}?tab=settings"
    assert regenerated.status_code == 303
    assert "Prog I" in settings.text
    assert code not in settings.text


@pytest.mark.anyio
async def test_owner_removes_a_member_from_the_members_tab() -> None:
    campus = Campus()
    classroom_id, _ = await campus.classroom()
    teacher = await campus.client_for(TEACHER)
    members = await teacher.get(f"/classes/{classroom_id}?tab=members")
    user_id = members.text.split("/members/")[1].split("/remove")[0]

    removed = await teacher.post(f"/classes/{classroom_id}/members/{user_id}/remove")
    student = await campus.client_for(STUDENT)

    assert removed.headers["location"] == f"/classes/{classroom_id}?tab=members"
    assert "66010001" in members.text
    assert (await student.get(f"/classes/{classroom_id}")).status_code == 404
