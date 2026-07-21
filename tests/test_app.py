"""Integration tests for the GReader application."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import app


@pytest.fixture()
def client():
    """Synchronous test client (httpx)."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


# ------------------------------------------------------------------
# GET /health
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_json_structure(client):
    response = await client.get("/health")
    data = response.json()
    assert data == {"status": "ok", "service": "greader"}


# ------------------------------------------------------------------
# GET /
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_dashboard_returns_200(client):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_dashboard_returns_html(client):
    response = await client.get("/")
    assert "text/html" in response.headers["content-type"]


@pytest.mark.anyio
async def test_dashboard_contains_greader(client):
    response = await client.get("/")
    assert "GReader" in response.text


@pytest.mark.anyio
async def test_dashboard_contains_tagline(client):
    response = await client.get("/")
    assert "AI-assisted assignment authoring" in response.text
