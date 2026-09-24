"""T-01 Problems/Summary and S-01 Problems/Summary filled from assignments."""

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.demo import DemoSeed, build_demo_app

from tests.fakes.auth import DEFAULT_PASSWORD
from tests.integration.forms import log_in


async def _client(app, email: str) -> AsyncClient:
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")
    await log_in(client, email, DEFAULT_PASSWORD)
    return client


@pytest.fixture()
def demo() -> tuple:
    seed = DemoSeed()
    return build_demo_app(seed), seed


@pytest.mark.anyio
async def test_t01_problems_lists_published_rows(demo) -> None:
    app, seed = demo
    teacher = await _client(app, seed.somchai.email)

    page = await teacher.get(f"/classes/{seed.programming_1.id}?tab=problems")

    assert page.status_code == 200
    assert "Published · 6" in page.text
    assert "4 · Binary search on sorted input" in page.text
    assert "4/6" in page.text and "6.0" in page.text
    assert 'data-state="T-01b"' not in page.text


@pytest.mark.anyio
async def test_t01_summary_shows_stats_and_score_table(demo) -> None:
    app, seed = demo
    teacher = await _client(app, seed.somchai.email)

    page = await teacher.get(f"/classes/{seed.programming_1.id}?tab=summary")

    assert "Top 5 most-failed problems" in page.text
    assert "75%" in page.text
    assert "Pimchanok Wong" in page.text


@pytest.mark.anyio
async def test_s01_problems_shows_badges_and_filters(demo) -> None:
    app, seed = demo
    student = await _client(app, seed.students[0].email)
    base = f"/classes/{seed.programming_1.id}?tab=problems"

    everything = await student.get(base)
    unstarted = await student.get(f"{base}&filter=not_started")
    submitted = await student.get(f"{base}&filter=submitted")

    assert "Resubmit needed" in everything.text
    assert "10/10" in everything.text
    assert "6 problems" in everything.text
    assert "Sum of a list" not in unstarted.text
    assert "Matrix transpose" in unstarted.text
    assert "Matrix transpose" not in submitted.text


@pytest.mark.anyio
async def test_s01_summary_counts_this_classroom(demo) -> None:
    app, seed = demo
    student = await _client(app, seed.students[0].email)

    page = await student.get(f"/classes/{seed.programming_1.id}?tab=summary")

    assert "4 / 6" in page.text
    assert "2 / 6" in page.text
    assert "7.8" in page.text


@pytest.mark.anyio
async def test_empty_classroom_shows_s01a_and_t01b() -> None:
    seed = DemoSeed()
    app = build_demo_app(seed)
    teacher = await _client(app, seed.somchai.email)
    classroom = app.state.classroom_service.create(
        app.state.auth_service.resolve_session(teacher.cookies["greader_session"]),
        course_code="01076099",
        course_name="Empty",
        section="1",
        semester="1/2569",
    )

    page = await teacher.get(f"/classes/{classroom.id}?tab=problems")

    assert 'data-state="T-01b"' in page.text
