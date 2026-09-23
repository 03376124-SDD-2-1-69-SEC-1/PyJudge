"""How a handler learns who is calling: `actor = current_actor(request)`.

This replaces `Depends()` for identity (AGENTS.md "Stack"): the handler calls it
explicitly, the same way `_service(request)` pulls a service off app.state.
"""

from fastapi import Request

from greader.core.auth.models import Actor, NotAuthenticatedError
from greader.core.auth.service import AuthService

SESSION_COOKIE = "greader_session"


def auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def current_actor(request: Request) -> Actor:
    """Resolve the session cookie, or raise NotAuthenticatedError."""
    token = request.cookies.get(SESSION_COOKIE)
    if token is None:
        raise NotAuthenticatedError
    return auth_service(request).resolve_session(token)
