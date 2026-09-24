"""CSRF protection for HTML form posts: one token source, one check.

Logged in: the synchronizer token stored on the Session (minted at login).
Not logged in (G-01 login, G-03 sign-up, resend link): a random token in the
`greader_csrf` cookie, echoed by the form (double-submit), so login and
sign-up forms cannot be posted from another site either.

Every POST page handler calls `require_csrf(request, csrf_token)` first; every
POST form renders `{{ csrf_field() }}` (tests/architecture checks both). The
JSON API does not use this: FastAPI parses JSON bodies only when the request
says `Content-Type: application/json`, which a cross-site form cannot send
without a CORS preflight, and no CORS origins are allowed.
"""

import hmac
import secrets

from fastapi import Request, Response

from greader.core.auth.current import SESSION_COOKIE, auth_service
from greader.core.auth.models import CsrfTokenError, NotAuthenticatedError

CSRF_COOKIE = "greader_csrf"
CSRF_FIELD = "csrf_token"
# Where a token minted during this request waits for its cookie.
_MINTED = "greader.minted_csrf_token"


def csrf_token(request: Request) -> str:
    """The token forms on this page must carry.

    For a visitor without a session and without a CSRF cookie, a fresh token
    is minted and remembered in the request scope; `set_anonymous_csrf_cookie`
    then stores it on the response.
    """
    session_token = request.cookies.get(SESSION_COOKIE)
    if session_token is not None:
        try:
            return auth_service(request).csrf_token_for(session_token)
        except NotAuthenticatedError:
            pass
    cookie = request.cookies.get(CSRF_COOKIE)
    if cookie is not None:
        return cookie
    return request.scope.setdefault(_MINTED, secrets.token_urlsafe(32))


def set_anonymous_csrf_cookie(request: Request, response: Response) -> None:
    """Store a token minted while rendering an anonymous page."""
    if _MINTED not in request.scope:
        return
    response.set_cookie(
        CSRF_COOKIE,
        request.scope[_MINTED],
        httponly=True,
        samesite="lax",
        secure=request.app.state.secure_cookies,
    )


def require_csrf(request: Request, submitted: str) -> None:
    """Refuse a form post whose token does not match (403)."""
    session_token = request.cookies.get(SESSION_COOKIE)
    expected = None
    if session_token is not None:
        try:
            expected = auth_service(request).csrf_token_for(session_token)
        except NotAuthenticatedError:
            expected = None
    if expected is None:
        expected = request.cookies.get(CSRF_COOKIE)
    if not submitted or expected is None:
        raise CsrfTokenError
    if not hmac.compare_digest(submitted, expected):
        raise CsrfTokenError
