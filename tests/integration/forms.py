"""Helpers for posting HTML forms the way a browser does: with the CSRF token."""

import re

from httpx import AsyncClient, Response

TOKEN = re.compile(r'name="csrf_token" value="([^"]+)"')


async def csrf_token(client: AsyncClient, page: str) -> str:
    """GET `page` (setting any cookies) and return its forms' token."""
    response = await client.get(page)
    match = TOKEN.search(response.text)
    assert match is not None, f"no csrf_token on {page}"
    return match.group(1)


async def post_form(
    client: AsyncClient, action: str, data: dict[str, str], *, page: str
) -> Response:
    """POST `data` to `action` with the token rendered on `page`."""
    token = await csrf_token(client, page)
    return await client.post(action, data={**data, "csrf_token": token})


async def log_in(client: AsyncClient, email: str, password: str) -> Response:
    return await post_form(
        client, "/login", {"email": email, "password": password}, page="/login"
    )
