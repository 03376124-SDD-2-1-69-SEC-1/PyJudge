"""Integration tests for the GReader application."""

import pytest
from httpx import ASGITransport, AsyncClient

from greader.assignments.seed import create_seed_repository
from greader.main import create_app


@pytest.fixture()
def client():
    """Synchronous test client (httpx)."""
    application = create_app(assignment_repo=create_seed_repository())
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


@pytest.mark.anyio
async def test_ai_studio_preserves_generation_form_contract(client):
    response = await client.get("/")
    body = response.text

    assert 'id="ai-form"' in body
    assert 'action="/assistant/generate"' in body
    assert 'name="prompt"' in body
    assert 'name="mode"' in body
    assert 'name="assignment_id"' in body
    assert 'value="full_assignment"' in body
    assert 'value="test_cases"' in body
    assert 'value="edge_cases"' in body


@pytest.mark.anyio
async def test_ai_studio_has_chat_workspace_and_draft_inspector(client):
    response = await client.get("/")
    body = response.text

    assert "AI Conversation" in body
    assert "Draft Inspector" in body
    assert "Sticky prompt composer" in body
    assert "Review actions" in body


@pytest.mark.anyio
async def test_ai_studio_uses_assignment_selector_for_context_modes(client):
    response = await client.get("/")
    body = response.text

    assert '<select id="assignment-id"' in body
    assert "Two Sum Optimized" in body
    assert 'value="two-sum-optimized"' in body


@pytest.mark.anyio
async def test_ai_studio_exposes_artifact_review_controls(client):
    response = await client.get("/")
    body = response.text

    assert 'id="save-artifact-button"' in body
    assert 'id="discard-artifact-button"' in body
    assert 'data-artifact-state="empty"' in body


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
    """The sidebar must contain the instructor workspace navigation items."""
    response = await client.get("/")
    body = response.text
    expected_items = [
        "Dashboard",
        "Assignments",
        "AI Studio",
        "Review",
        "Analytics",
        "Settings",
    ]
    for item in expected_items:
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
