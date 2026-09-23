"""scripts/demo.py builds a clickable app from fakes and a seed."""

import pytest
from httpx import ASGITransport, AsyncClient
from scripts.demo import DemoSeed, build_demo_app


@pytest.mark.anyio
async def test_every_verified_demo_account_logs_in_and_lands() -> None:
    seed = DemoSeed()
    app = build_demo_app(seed)
    verified = [a for a in seed.accounts if "unverified" not in a.label]

    for account in verified:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            login = await client.post(
                "/login", data={"email": account.email, "password": account.password}
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
