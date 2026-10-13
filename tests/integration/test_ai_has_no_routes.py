"""The AI module is reached through core ports; it serves no HTTP routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.fakes.app import build_app

VECTOR_PATHS = ("/api/v1/knowledge-sources", "/api/v1/knowledge-chunks/search")


@pytest.fixture()
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=build_app()), base_url="http://testserver"
    ) as test_client:
        yield test_client


@pytest.mark.anyio
@pytest.mark.parametrize("path", VECTOR_PATHS)
async def test_anonymous_post_to_vector_path_is_not_found(client, path):
    response = await client.post(path, json={})
    assert response.status_code == 404


def test_vector_paths_are_not_in_openapi():
    document = build_app().openapi()
    for path in VECTOR_PATHS:
        assert path not in document["paths"]
