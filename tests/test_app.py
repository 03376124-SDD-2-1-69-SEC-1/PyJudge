"""Integration tests for the GReader application."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.main import create_app


@pytest.fixture()
def client():
    """Synchronous test client (httpx)."""
    application = create_app()
    transport = ASGITransport(app=application)
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


# ------------------------------------------------------------------
# Layout & Sidebar (Task 2)
# ------------------------------------------------------------------


@pytest.mark.anyio
async def test_compiled_stylesheet_is_linked(client):
    """The compiled Tailwind stylesheet must be referenced in the HTML."""
    response = await client.get("/")
    assert "/static/css/app.css" in response.text


@pytest.mark.anyio
async def test_sidebar_contains_navigation_items(client):
    """The sidebar must contain all five navigation items."""
    response = await client.get("/")
    body = response.text
    for item in ["Dashboard", "Assignments", "Review Queue", "Analytics", "Settings"]:
        assert item in body, f"Sidebar navigation item '{item}' not found"


@pytest.mark.anyio
async def test_sidebar_contains_product_name(client):
    """The product name 'GReader' must be visible in the sidebar."""
    response = await client.get("/")
    assert "GReader" in response.text


@pytest.mark.anyio
async def test_static_stylesheet_returns_200(client):
    """The compiled CSS file must be served at /static/css/app.css."""
    response = await client.get("/static/css/app.css")
    assert response.status_code == 200
