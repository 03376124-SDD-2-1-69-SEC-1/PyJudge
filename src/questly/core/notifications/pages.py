"""G-02a: the notifications dropdown in the shared header, and its two POSTs.

The header is on every page, so it asks for its own data: `base.html` calls the
Jinja global `header_notifications(request)` and no page handler passes it.
"""

import logging
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from questly.core.auth.csrf import require_csrf
from questly.core.auth.current import current_actor
from questly.core.notifications.menu import NotificationMenu, build_menu
from questly.core.notifications.service import (
    DueSoonService,
    NotificationNotFoundError,
    NotificationService,
)

router = APIRouter(tags=["pages"], include_in_schema=False)

logger = logging.getLogger(__name__)

EMPTY_MENU = NotificationMenu(unread_count=0, due_soon=(), recent=())


def _notifications(request: Request) -> NotificationService:
    return request.app.state.notification_service


def _due_soon(request: Request) -> DueSoonService:
    return request.app.state.due_soon_service


def local_path(target: str) -> str:
    """`target` if it is a path on this site, else "/" (open-redirect guard).

    A local path starts with one `/`. `//host` and `/\\host` are read by
    browsers as another host, and a tab or newline inside is stripped before
    that reading, so anything unprintable is refused too.
    """
    if not target.startswith("/") or target.startswith("//"):
        return "/"
    if "\\" in target or not target.isprintable():
        return "/"
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return "/"
    return target


def _return_to(request: Request) -> str:
    """Where the header's forms send the user back to: the page being drawn."""
    if request.method != "GET":
        return "/"
    query = f"?{request.url.query}" if request.url.query else ""
    return local_path(f"{request.url.path}{query}")


def header_notifications(request: Request) -> NotificationMenu:
    """The bell's data for the logged-in user; the page must render without it."""
    try:
        actor = current_actor(request)
        return build_menu(
            _notifications(request).list_for_user(actor.user_id),
            _due_soon(request).due_soon(actor),
            return_to=_return_to(request),
        )
    except Exception:
        logger.exception("could not load the header notifications")
        return EMPTY_MENU


def _back(next_path: str) -> RedirectResponse:
    return RedirectResponse(
        local_path(next_path), status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/notifications/read-all")
def mark_all_read(
    request: Request,
    csrf_token: Annotated[str, Form()] = "",
    next_path: Annotated[str, Form(alias="next")] = "/",
) -> RedirectResponse:
    """G-02a "Mark all read"."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    _notifications(request).mark_all_read(actor.user_id)
    return _back(next_path)


@router.post("/notifications/{notification_id}/read")
def mark_read(
    request: Request,
    notification_id: int,
    csrf_token: Annotated[str, Form()] = "",
    next_path: Annotated[str, Form(alias="next")] = "/",
) -> RedirectResponse:
    """G-02a: mark one notification read; someone else's is a 404."""
    require_csrf(request, csrf_token)
    actor = current_actor(request)
    try:
        _notifications(request).mark_read(actor.user_id, notification_id)
    except NotificationNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from None
    return _back(next_path)
