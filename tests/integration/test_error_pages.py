"""HTTP tests for G-05, the branded error page every browser error lands on."""

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from tests.fakes.app import build_app


def _client(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


def _app_with_boom():
    app = build_app()
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    @router.get("/api/v1/boom")
    def api_boom() -> None:
        raise RuntimeError("secret internals")

    app.include_router(router)
    return app


@pytest.mark.anyio
async def test_unknown_page_renders_g05_404() -> None:
    async with _client(build_app()) as client:
        response = await client.get("/no-such-page")

    assert response.status_code == 404
    assert 'data-page="G-05"' in response.text
    assert 'data-status="404"' in response.text
    assert 'href="/"' in response.text


@pytest.mark.anyio
async def test_wrong_method_renders_g05_405() -> None:
    async with _client(build_app()) as client:
        response = await client.put("/login")

    assert response.status_code == 405
    assert 'data-status="405"' in response.text


@pytest.mark.anyio
async def test_unhandled_error_renders_g05_500_without_leaking_the_cause() -> None:
    transport = ASGITransport(app=_app_with_boom(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert 'data-status="500"' in response.text
    assert 'href="/boom"' in response.text
    assert "secret internals" not in response.text


@pytest.mark.anyio
async def test_api_errors_stay_json() -> None:
    transport = ASGITransport(app=_app_with_boom(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        missing = await client.get("/api/v1/no-such-route")
        broken = await client.get("/api/v1/boom")

    assert missing.status_code == 404
    assert "detail" in missing.json()
    assert broken.status_code == 500
    assert broken.json()["detail"]["code"] == "internal_error"


@pytest.mark.anyio
async def test_forbidden_page_renders_g05_403() -> None:
    async with _client(build_app()) as client:
        response = await client.post("/login", data={"email": "a", "password": "b"})

    assert response.status_code == 403
    assert 'data-status="403"' in response.text
    assert "ฟอร์มนี้หมดอายุแล้ว" in response.text
