"""G-02a: the notifications dropdown in the shared header, per role, and its POSTs."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from questly.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    Schedule,
    TestCase,
)
from questly.core.auth.models import Actor, Role
from questly.core.notifications.models import NotificationKind
from tests.fakes.app import build_app
from tests.fakes.auth import DEFAULT_PASSWORD, FakeAuthRepository, FakeClock, seed_user
from tests.integration.forms import log_in, post_form

DEADLINE = datetime(2026, 10, 15, 16, 59, tzinfo=UTC)
TEACHER = "somchai.p@kmitl.ac.th"
STUDENT = "66010001@kmitl.ac.th"
CLASSMATE = "66010002@kmitl.ac.th"
ADMIN = "admin@kmitl.ac.th"
BADGE = re.compile(r'<span class="badge badge-accent">(\d+)</span>')


class Campus:
    """Somchai publishes "Binary search" to Sec 1, where two Students are Members."""

    def __init__(self) -> None:
        users = FakeAuthRepository()
        accounts = {}
        for email, name, role in [
            (TEACHER, "Somchai Prasert", Role.INSTRUCTOR),
            (STUDENT, "Nattapong Suwan", Role.STUDENT),
            (CLASSMATE, "Pimchanok Wong", Role.STUDENT),
            (ADMIN, "Admin", Role.ADMIN),
        ]:
            user = seed_user(users, email=email, full_name=name, role=role)
            accounts[email] = Actor(
                user_id=user.id, role=role, full_name=name, email=email
            )
        self.clock = FakeClock()
        self.app = build_app(auth_repository=users, clock=self.clock)
        classrooms = self.app.state.classroom_service
        self.classroom = classrooms.create(
            accounts[TEACHER],
            course_code="01076001",
            course_name="Programming I",
            section="1",
            semester="1/2569",
        )
        classrooms.join(accounts[STUDENT], self.classroom.join_code)
        classrooms.join(accounts[CLASSMATE], self.classroom.join_code)
        published = self.app.state.assignment_service.publish(
            accounts[TEACHER],
            AssignmentContent(
                title="Binary search",
                problem_statement="Print the index of x, or -1.",
                difficulty=Difficulty.MEDIUM,
                test_cases=[TestCase(input_data="1\n4\n4", expected_output="0")],
            ),
            Schedule(deadline=DEADLINE),
            [self.classroom.id],
        )
        self.assignment_id = published.assignment.id
        self.problem_href = (
            f"/classes/{self.classroom.id}/assignments/{self.assignment_id}"
        )

    async def client_for(self, email: str) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://testserver"
        )
        await log_in(client, email, DEFAULT_PASSWORD)
        return client

    async def notify(self) -> None:
        """Instructor reminds the Members: one more stored notification each."""
        teacher = await self.client_for(TEACHER)
        await teacher.post(
            f"/api/v1/classrooms/{self.classroom.id}"
            f"/assignments/{self.assignment_id}/notify"
        )

    async def notification_ids(self, client: AsyncClient) -> list[int]:
        listed = await client.get("/api/v1/notifications")
        return [item["id"] for item in listed.json()["items"]]

    async def unread(self, client: AsyncClient) -> int:
        listed = await client.get("/api/v1/notifications")
        return sum(1 for item in listed.json()["items"] if item["read_at"] is None)


def dropdown(html: str) -> str:
    """Just the G-02a <details> of a rendered page."""
    return html.split('data-page="G-02a"', 1)[1].split("</details>", 1)[0]


def badge_count(html: str) -> int:
    match = BADGE.search(dropdown(html))
    return int(match.group(1)) if match else 0


@pytest.mark.anyio
async def test_a_student_sees_the_bell_the_count_and_the_latest_items() -> None:
    campus = Campus()
    await campus.notify()
    student = await campus.client_for(STUDENT)

    page = await student.get("/classes")

    assert page.status_code == 200
    menu = dropdown(page.text)
    assert "<details" in page.text and 'aria-label="Notifications"' in menu
    assert badge_count(page.text) == 2
    assert "Reminder: Binary search" in menu
    assert "New problem: Binary search" in menu
    assert menu.index("Reminder:") < menu.index("New problem:")
    assert f'href="{campus.problem_href}"' in menu
    assert "No notifications yet." not in menu
    assert "Mark all read" in menu


@pytest.mark.anyio
async def test_the_bell_has_no_javascript_and_no_popover() -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)

    page = await student.get("/classes")

    assert 'popovertarget="notifications"' not in page.text
    assert "<script" not in page.text


@pytest.mark.anyio
async def test_an_updated_notification_shows_the_reason() -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)
    campus.app.state.notification_service.create(
        user_id=(await student.get("/api/v1/auth/me")).json()["id"],
        kind=NotificationKind.ASSIGNMENT_UPDATED,
        payload={
            "classroom_id": campus.classroom.id,
            "assignment_id": campus.assignment_id,
            "title": "Binary search",
            "reason": "Sample 2 was wrong",
        },
    )

    menu = dropdown((await student.get("/classes")).text)

    assert "Problem updated: Binary search" in menu
    assert "Sample 2 was wrong" in menu


@pytest.mark.anyio
async def test_due_soon_is_listed_first_and_only_for_a_student() -> None:
    campus = Campus()
    campus.clock.current = DEADLINE - timedelta(hours=2)
    student = await campus.client_for(STUDENT)
    teacher = await campus.client_for(TEACHER)

    student_menu = dropdown((await student.get("/classes")).text)
    teacher_menu = dropdown((await teacher.get("/classes")).text)

    assert "Deadline tomorrow: Binary search" in student_menu
    assert student_menu.index("Deadline tomorrow:") < student_menu.index("New problem:")
    assert "Deadline tomorrow" not in teacher_menu


@pytest.mark.anyio
async def test_due_soon_alone_is_not_counted_as_unread_and_is_not_empty() -> None:
    campus = Campus()
    campus.clock.current = DEADLINE - timedelta(hours=2)
    student = await campus.client_for(STUDENT)
    await student.post("/api/v1/notifications/read-all")

    page = await student.get("/classes")

    assert badge_count(page.text) == 0
    assert "Deadline tomorrow: Binary search" in page.text
    assert "No notifications yet." not in dropdown(page.text)


@pytest.mark.anyio
async def test_an_instructor_sees_the_empty_state_and_no_badge() -> None:
    campus = Campus()
    teacher = await campus.client_for(TEACHER)

    page = await teacher.get("/classes")

    assert page.status_code == 200
    menu = dropdown(page.text)
    assert "No notifications yet." in menu
    assert badge_count(page.text) == 0
    assert "Mark all read" not in menu


@pytest.mark.anyio
async def test_an_admin_page_still_renders_with_the_header() -> None:
    campus = Campus()
    admin = await campus.client_for(ADMIN)

    page = await admin.get("/admin/settings")

    assert page.status_code == 200
    assert "No notifications yet." in dropdown(page.text)


@pytest.mark.anyio
async def test_a_failing_notification_lookup_does_not_break_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)

    def explode(user_id: int) -> list:
        raise RuntimeError("database is down")

    monkeypatch.setattr(campus.app.state.notification_service, "list_for_user", explode)

    page = await student.get("/classes")

    assert page.status_code == 200
    assert "No notifications yet." in dropdown(page.text)


@pytest.mark.anyio
async def test_the_forms_return_to_the_page_they_were_drawn_on() -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)

    page = await student.get(f"/classes/{campus.classroom.id}?tab=summary")

    expected = f'name="next" value="/classes/{campus.classroom.id}?tab=summary"'
    assert dropdown(page.text).count(expected) == 2


@pytest.mark.anyio
async def test_mark_all_read_clears_the_badge_and_returns_to_next() -> None:
    campus = Campus()
    await campus.notify()
    student = await campus.client_for(STUDENT)
    classmate = await campus.client_for(CLASSMATE)

    response = await post_form(
        student,
        "/notifications/read-all",
        {"next": "/classes?filter=archived"},
        page="/classes",
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/classes?filter=archived"
    assert badge_count((await student.get("/classes")).text) == 0
    assert await campus.unread(student) == 0
    assert await campus.unread(classmate) == 2


@pytest.mark.anyio
async def test_mark_one_read_drops_its_button_and_lowers_the_count() -> None:
    campus = Campus()
    await campus.notify()
    student = await campus.client_for(STUDENT)
    newest, older = await campus.notification_ids(student)

    page = await student.get("/classes")
    assert f'action="/notifications/{newest}/read"' in dropdown(page.text)
    response = await post_form(
        student, f"/notifications/{newest}/read", {"next": "/classes"}, page="/classes"
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/classes"
    after = await student.get("/classes")
    assert badge_count(after.text) == 1
    assert f'action="/notifications/{newest}/read"' not in dropdown(after.text)
    assert f'action="/notifications/{older}/read"' in dropdown(after.text)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.example/",
        "//evil.example",
        "/\\evil.example",
        "javascript:alert(1)",
        "evil.example",
        "/\t/evil.example",
        "",
    ],
)
async def test_a_hostile_next_falls_back_to_the_front_page(hostile: str) -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)
    (own,) = await campus.notification_ids(student)

    read_all = await post_form(
        student, "/notifications/read-all", {"next": hostile}, page="/classes"
    )
    one = await post_form(
        student, f"/notifications/{own}/read", {"next": hostile}, page="/classes"
    )

    assert read_all.status_code == one.status_code == 303
    assert read_all.headers["location"] == one.headers["location"] == "/"


@pytest.mark.anyio
async def test_a_post_without_the_csrf_token_is_refused_and_changes_nothing() -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)
    (own,) = await campus.notification_ids(student)

    read_all = await student.post("/notifications/read-all", data={"next": "/"})
    one = await student.post(f"/notifications/{own}/read", data={"next": "/"})
    wrong = await student.post(
        "/notifications/read-all", data={"next": "/", "csrf_token": "forged"}
    )

    assert read_all.status_code == one.status_code == wrong.status_code == 403
    assert await campus.unread(student) == 1


@pytest.mark.anyio
async def test_nobody_can_mark_another_users_notification_read() -> None:
    campus = Campus()
    student = await campus.client_for(STUDENT)
    classmate = await campus.client_for(CLASSMATE)
    (theirs,) = await campus.notification_ids(classmate)

    stolen = await post_form(
        student, f"/notifications/{theirs}/read", {"next": "/"}, page="/classes"
    )
    missing = await post_form(
        student, "/notifications/999999/read", {"next": "/"}, page="/classes"
    )

    assert stolen.status_code == missing.status_code == 404
    assert await campus.unread(classmate) == 1


@pytest.mark.anyio
async def test_a_logged_out_post_is_sent_to_the_login_page() -> None:
    campus = Campus()
    async with AsyncClient(
        transport=ASGITransport(app=campus.app), base_url="http://testserver"
    ) as anonymous:
        response = await post_form(
            anonymous, "/notifications/read-all", {"next": "/"}, page="/login"
        )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"
