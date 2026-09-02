"""Integration tests for the shared web layout."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import create_app


@pytest.mark.anyio
async def test_home_uses_shared_layout_without_authored_javascript() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "GReader Team Scaffold" in response.text
    assert 'href="/docs"' in response.text
    assert "<script" not in response.text.lower()
