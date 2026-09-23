"""Integration tests for the shared web layout."""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from tests.fakes.app import build_app

STATIC_DIR = Path("src/greader/web/static")


@pytest.mark.anyio
async def test_stylesheet_url_carries_the_file_version() -> None:
    """A rebuilt app.css must reach the browser without a manual cache clear."""
    stylesheet = STATIC_DIR / "css" / "app.css"
    version = int(stylesheet.stat().st_mtime)
    transport = ASGITransport(app=build_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        page = await client.get("/login")
        css = await client.get(f"/static/css/app.css?v={version}")

    assert f'href="/static/css/app.css?v={version}"' in page.text
    assert css.status_code == 200
    assert ".btn-primary" in css.text


def test_asset_url_changes_when_the_file_changes(tmp_path, monkeypatch) -> None:
    import greader.main as main

    (tmp_path / "css").mkdir()
    built = tmp_path / "css" / "app.css"
    built.write_text("a{}")
    monkeypatch.setattr(main, "_STATIC_DIR", tmp_path)
    os.utime(built, (1_000, 1_000))
    before = main.asset_url("css/app.css")
    os.utime(built, (2_000, 2_000))

    assert before == "/static/css/app.css?v=1000"
    assert main.asset_url("css/app.css") == "/static/css/app.css?v=2000"
