"""scripts/demo.py builds a clickable app from fakes and a seed."""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.demo import DemoSeed, build_demo_app

from questly.core.auth.models import Actor
from tests.fakes.auth import DEFAULT_NOW, FakeClock
from tests.integration.forms import post_form


@pytest.mark.anyio
async def test_every_verified_demo_account_logs_in_and_lands() -> None:
    seed = DemoSeed()
    app = build_demo_app(seed)
    verified = [a for a in seed.accounts if "unverified" not in a.label]

    for account in verified:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            login = await post_form(
                client,
                "/login",
                {"email": account.email, "password": account.password},
                page="/login",
            )
            landing = await client.get(login.headers["location"])

        assert login.status_code == 303, account.label
        if login.headers["location"] == "/classes":
            assert landing.status_code == 200, account.label


@pytest.mark.anyio
async def test_login_page_lists_the_seeded_accounts() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_demo_app()), base_url="http://testserver"
    ) as client:
        page = await client.get("/login")

    assert 'data-demo="log-in-as"' in page.text
    assert "Somchai Prasert · instructor" in page.text


@pytest.mark.anyio
async def test_seed_matches_the_prototype_shape() -> None:
    seed = DemoSeed()
    somchai_rooms = seed.classrooms.list_owned_by(seed.somchai.id)

    assert len(seed.students) == 10
    assert [c.label for c in somchai_rooms] == ["01076001 · Sec 1", "01076002 · Sec 2"]
    assert somchai_rooms[0].join_code == "X7K29B"


@pytest.mark.parametrize(
    "now",
    [
        DEFAULT_NOW,
        datetime(2027, 2, 14, 9, 0, tzinfo=UTC),
        datetime(2030, 6, 1, 9, 0, tzinfo=UTC),
    ],
    ids=["prototype-day", "next-year", "2030"],
)
def test_seeded_deadlines_follow_the_clock(now: datetime) -> None:
    clock = FakeClock(now)
    seed = DemoSeed(clock=clock)
    app = build_demo_app(seed)
    teacher = seed.somchai
    actor = Actor(teacher.id, teacher.role, teacher.full_name, teacher.email)
    service = app.state.assignment_service
    rows = service.problems(actor, seed.programming_1.id).problems

    closed = {
        row.assignment.title: service.problem(
            actor, seed.programming_1.id, row.assignment.id
        ).posting.is_closed(clock.now())
        for row in rows
    }

    # Three problems are past their deadline; "Reverse a string" takes late
    # work so it stays open, and the last three are still ahead.
    assert closed == {
        "Sum of a list": True,
        "Reverse a string": False,
        "Count word frequency": True,
        "Binary search on sorted input": False,
        "Matrix transpose": False,
        "Stack with min()": False,
    }
