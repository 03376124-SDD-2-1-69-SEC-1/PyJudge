"""T-05 edit (05a extend the deadline), the T-02 search and "Notify students"."""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.demo import BINARY_SEARCH, UPDATE_REASON, DemoSeed, build_demo_app

from questly.core.assignments.models import Assignment
from questly.core.auth.models import Actor
from tests.fakes.auth import DEFAULT_PASSWORD, FakeClock
from tests.integration.forms import log_in, post_form

BS = BINARY_SEARCH + 1  # Binary search is Sec 1's problem 4


class Demo:
    def __init__(self) -> None:
        self.seed = DemoSeed(clock=FakeClock())
        self.app = build_demo_app(self.seed)
        self.sec1 = self.seed.programming_1.id
        self.sec2 = self.seed.programming_2.id
        teacher = self.seed.somchai
        self.teacher = Actor(teacher.id, teacher.role, teacher.full_name, teacher.email)
        self.service = self.app.state.assignment_service

    async def client(self, email: str) -> AsyncClient:
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://testserver"
        )
        await log_in(client, email, DEFAULT_PASSWORD)
        return client

    def assignment(self, number: int) -> Assignment:
        problems = self.service.problems(self.teacher, self.sec1)
        return next(p for p in problems.problems if p.number == number).assignment

    def url(self, number: int, classroom_id: int | None = None) -> str:
        """T-02 of Sec 1 problem `number`, or of the same problem in another room."""
        if classroom_id is None:
            classroom_id = self.sec1
        return f"/classes/{classroom_id}/assignments/{self.assignment(number).id}"

    def posting(self, classroom_id: int, number: int):
        return self.service.problem(
            self.teacher, classroom_id, self.assignment(number).id
        ).posting

    def form(self, number: int, **overrides: object) -> dict[str, object]:
        """What the T-05 form posts when nothing is changed."""
        assignment = self.assignment(number)
        tests = assignment.test_cases
        data: dict[str, object] = {
            "title": assignment.title,
            "problem_statement": assignment.problem_statement,
            "difficulty": assignment.difficulty.value,
            "topic_id": "",
            "reason": "Fixed a typo.",
            "kind": [t.kind.value for t in tests],
            "input_data": [t.input_data for t in tests],
            "expected_output": [t.expected_output for t in tests],
            "note": [t.note for t in tests],
            "test_case_id": [str(t.id) for t in tests],
            "time_limit_s": "1.0",
            "language": "python3",
            "posting_id": [
                self.posting(self.sec1, number).id,
                self.posting(self.sec2, number).id,
            ],
            "extend_to": ["2026-12-01T23:59", "2026-12-01T23:59"],
        }
        return {**data, **overrides}


@pytest.fixture()
def demo() -> Demo:
    return Demo()


def emails(demo: Demo) -> dict[str, str]:
    return {
        "teacher": demo.seed.somchai.email,
        "student": demo.seed.students[0].email,
        "warunee": demo.seed.warunee.email,
        "sec2_student": demo.seed.students[7].email,
    }


async def post(
    client: AsyncClient, url: str, data: dict[str, object], *, page: str | None = None
):
    return await post_form(client, url, data, page=page or url)  # type: ignore[arg-type]


# ---- T-05 --------------------------------------------------------------------


@pytest.mark.anyio
async def test_t05_shows_the_problem_the_banner_and_the_05a_dialog(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    page = await client.get(demo.url(BS) + "/edit")

    assert page.status_code == 200
    assert 'data-page="T-05"' in page.text and 'data-page="T-05a"' in page.text
    assert "Binary search on sorted input" in page.text
    assert "4 students have already submitted" in page.text
    assert "Version becomes v3 in Version history" in page.text
    assert "A notification is sent to 10 students" in page.text
    assert "Programming I · Sec 1 / Problem 4 / Edit" in page.text
    assert 'popovertarget="t05a"' in page.text
    assert "<script" not in page.text


@pytest.mark.anyio
async def test_t05_precheck_is_the_classroom_being_edited_from(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    sec1_id = demo.posting(demo.sec1, BS).id
    sec2_id = demo.posting(demo.sec2, BS).id

    page = await client.get(demo.url(BS) + "/edit")
    other = await client.get(demo.url(BS, demo.sec2) + "/edit")

    assert f'name="extend" checked value="{sec1_id}"' in page.text
    assert f'name="extend" checked value="{sec2_id}"' not in page.text
    assert f'name="extend" checked value="{sec2_id}"' in other.text


@pytest.mark.anyio
async def test_t02_links_to_t05(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    page = await client.get(demo.url(BS))

    assert f'href="{demo.url(BS)}/edit"' in page.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("who", "status"),
    [("student", 403), ("warunee", 404), ("sec2_student", 404)],
)
async def test_t05_get_by_role(demo: Demo, who: str, status: int) -> None:
    client = await demo.client(emails(demo)[who])

    response = await client.get(demo.url(BS) + "/edit")

    assert response.status_code == status


@pytest.mark.anyio
async def test_t05_unknown_problem_is_404(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await client.get(f"/classes/{demo.sec1}/assignments/99999/edit")

    assert response.status_code == 404


@pytest.mark.anyio
async def test_t05_extend_one_classroom_keeps_the_other(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    url = demo.url(BS)
    sec1_before = demo.posting(demo.sec1, BS).schedule.deadline
    sec2_before = demo.posting(demo.sec2, BS).schedule.deadline

    response = await post(
        client,
        url + "/edit",
        demo.form(
            BS,
            title="Binary search, revised",
            reason="Clarified the statement.",
            extend=[demo.posting(demo.sec1, BS).id],
        ),
    )

    assert response.status_code == 303 and response.headers["location"] == url
    assert demo.assignment(BS).title == "Binary search, revised"
    assert demo.assignment(BS).current_version == 3
    # 23:59 Bangkok on 1 Dec is 16:59 UTC.
    assert demo.posting(demo.sec1, BS).schedule.deadline == datetime(
        2026, 12, 1, 16, 59, tzinfo=UTC
    )
    assert demo.posting(demo.sec1, BS).schedule.deadline != sec1_before
    assert demo.posting(demo.sec2, BS).schedule.deadline == sec2_before
    versions = await client.get(url + "?tab=versions")
    assert (
        "Clarified the statement." in versions.text and "v3 · current" in versions.text
    )


@pytest.mark.anyio
async def test_t05_keep_the_current_deadlines(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    before = [
        demo.posting(room, BS).schedule.deadline for room in (demo.sec1, demo.sec2)
    ]

    response = await post(client, demo.url(BS) + "/edit", demo.form(BS))

    assert response.status_code == 303
    assert demo.assignment(BS).current_version == 3
    after = [
        demo.posting(room, BS).schedule.deadline for room in (demo.sec1, demo.sec2)
    ]
    assert after == before


@pytest.mark.anyio
async def test_t05_save_keeps_test_case_ids_and_marks_resubmit_needed(
    demo: Demo,
) -> None:
    client = await demo.client(demo.seed.somchai.email)
    ids = [t.id for t in demo.assignment(BS).test_cases]

    await post(client, demo.url(BS) + "/edit", demo.form(BS))
    page = await client.get(demo.url(BS))

    assert [t.id for t in demo.assignment(BS).test_cases] == ids
    assert page.text.count("Resubmit needed") >= 4


@pytest.mark.anyio
async def test_t05_deleting_a_row_and_adding_a_new_one(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    before = demo.assignment(BS).test_cases
    data = demo.form(BS, delete=["0"])
    data["kind"] = [*data["kind"], "edge"]
    data["input_data"] = [*data["input_data"], "new input"]
    data["expected_output"] = [*data["expected_output"], "new output"]
    data["note"] = [*data["note"], "new row"]
    data["test_case_id"] = [*data["test_case_id"], ""]

    response = await post(client, demo.url(BS) + "/edit", data)

    assert response.status_code == 303
    after = demo.assignment(BS).test_cases
    assert len(after) == len(before)  # one removed, one added
    assert before[0].id not in [t.id for t in after]
    assert (after[-1].input_data, after[-1].note) == ("new input", "new row")


@pytest.mark.anyio
async def test_t05_blank_reason_is_a_422_on_the_page(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    url = demo.url(BS)

    response = await post(
        client,
        url + "/edit",
        demo.form(BS, title="Never saved", reason="   ", extend=[]),
    )

    assert response.status_code == 422
    assert 'data-page="T-05"' in response.text
    assert "A reason for the change is required." in response.text
    assert "Never saved" in response.text  # the form keeps what was typed
    assert demo.assignment(BS).title == "Binary search on sorted input"
    assert demo.assignment(BS).current_version == 2


@pytest.mark.anyio
async def test_t05_ticked_classroom_without_a_date_is_a_422(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await post(
        client,
        demo.url(BS) + "/edit",
        demo.form(
            BS,
            extend=[demo.posting(demo.sec1, BS).id],
            extend_to=["", ""],
        ),
    )

    assert response.status_code == 422
    assert "Choose a new deadline" in response.text
    assert demo.assignment(BS).current_version == 2


@pytest.mark.anyio
async def test_t05_invalid_content_is_a_422_not_a_500(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await post(
        client, demo.url(BS) + "/edit", demo.form(BS, title="  ", extend=[])
    )

    assert response.status_code == 422 and "A title is required." in response.text


@pytest.mark.anyio
async def test_t05_add_row_re_renders_without_saving(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await post(
        client,
        demo.url(BS) + "/edit",
        demo.form(BS, title="Typed but not saved", action="add_hidden"),
    )

    assert response.status_code == 200
    assert "Typed but not saved" in response.text
    assert demo.assignment(BS).title == "Binary search on sorted input"
    assert demo.assignment(BS).current_version == 2


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("who", "status"),
    [("student", 403), ("warunee", 404), ("sec2_student", 404)],
)
async def test_t05_post_by_role_changes_nothing(
    demo: Demo, who: str, status: int
) -> None:
    client = await demo.client(emails(demo)[who])
    url = demo.url(BS)

    # The token comes from a page every one of these users may open.
    response = await post(
        client, url + "/edit", demo.form(BS, title="Hacked"), page="/classes"
    )

    assert response.status_code == status
    assert demo.assignment(BS).title == "Binary search on sorted input"


@pytest.mark.anyio
async def test_t05_post_without_the_csrf_token_is_403(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await client.post(demo.url(BS) + "/edit", data=demo.form(BS))

    assert response.status_code == 403
    assert demo.assignment(BS).current_version == 2


@pytest.mark.anyio
async def test_t05_the_version_reason_reaches_the_student(demo: Demo) -> None:
    teacher = await demo.client(demo.seed.somchai.email)
    student = await demo.client(demo.seed.students[1].email)

    await post(
        teacher, demo.url(BS) + "/edit", demo.form(BS, reason="Sample 2 was wrong.")
    )
    page = await student.get(demo.url(BS))

    assert "Sample 2 was wrong." in page.text
    assert UPDATE_REASON not in page.text


# ---- T-02 search --------------------------------------------------------------


@pytest.mark.anyio
async def test_t02_search_by_name_or_student_id(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)
    url = demo.url(BS)

    by_name = await client.get(url + "?q=pimchanok")
    by_id = await client.get(url + "?q=66010003")
    everyone = await client.get(url)

    assert "Pimchanok Wong" in by_name.text and "Nattapong Suwan" not in by_name.text
    assert "Kittisak Rat" in by_id.text and "Pimchanok Wong" not in by_id.text
    assert "Nattapong Suwan" in everyone.text and "Pimchanok Wong" in everyone.text
    assert "4 / 6" in by_name.text  # the totals ignore the search


@pytest.mark.anyio
async def test_t02_search_keeps_the_tab_and_the_term(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    page = await client.get(demo.url(BS) + "?tab=results&q=wong")

    assert 'method="get"' in page.text
    assert 'name="tab" value="results"' in page.text
    assert 'name="q" value="wong"' in page.text


@pytest.mark.anyio
async def test_t02_search_with_no_match_shows_an_empty_state(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    page = await client.get(demo.url(BS) + "?q=zzz")

    assert page.status_code == 200
    assert 'data-state="T-02-search"' in page.text
    assert "No students match “zzz”" in page.text
    assert "Nattapong Suwan" not in page.text


@pytest.mark.anyio
async def test_t02_search_is_ignored_for_a_student(demo: Demo) -> None:
    client = await demo.client(demo.seed.students[0].email)

    page = await client.get(demo.url(BS) + "?q=zzz")

    assert page.status_code == 200 and 'data-page="S-02"' in page.text


# ---- T-02c Notify students -------------------------------------------------------


@pytest.mark.anyio
async def test_t02c_offers_notify_and_the_post_notifies_every_member(
    demo: Demo,
) -> None:
    teacher = await demo.client(demo.seed.somchai.email)
    student = await demo.client(demo.seed.students[0].email)
    url = demo.url(6)
    before = len((await student.get("/api/v1/notifications")).json()["items"])

    empty = await teacher.get(url)
    response = await post(teacher, url + "/notify", {}, page=url)
    after_page = await teacher.get(response.headers["location"])
    after = (await student.get("/api/v1/notifications")).json()["items"]

    assert 'data-state="T-02c"' in empty.text
    assert f'action="{url}/notify"' in empty.text and "Notify students" in empty.text
    assert response.status_code == 303
    assert response.headers["location"] == url + "?notified=1"
    assert "Students were notified about this problem." in after_page.text
    assert len(after) == before + 1
    assert after[0]["kind"] == "assignment_notified"


@pytest.mark.anyio
async def test_notified_confirmation_is_only_shown_when_asked(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    page = await client.get(demo.url(6))

    assert "Students were notified" not in page.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("who", "status"),
    [("student", 403), ("warunee", 404), ("sec2_student", 404)],
)
async def test_notify_by_role(demo: Demo, who: str, status: int) -> None:
    client = await demo.client(emails(demo)[who])
    member = await demo.client(demo.seed.students[1].email)
    before = len((await member.get("/api/v1/notifications")).json()["items"])

    response = await post(client, demo.url(6) + "/notify", {}, page="/classes")

    assert response.status_code == status
    after = len((await member.get("/api/v1/notifications")).json()["items"])
    assert after == before


@pytest.mark.anyio
async def test_notify_without_the_csrf_token_is_403(demo: Demo) -> None:
    client = await demo.client(demo.seed.somchai.email)

    response = await client.post(demo.url(6) + "/notify")

    assert response.status_code == 403
