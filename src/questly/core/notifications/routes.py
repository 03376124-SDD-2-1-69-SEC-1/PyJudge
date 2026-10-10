"""HTTP routes for Notifications."""

from fastapi import APIRouter, HTTPException, Request, status

from questly.core.auth.current import current_actor
from questly.core.notifications.models import Notification
from questly.core.notifications.schemas import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationResponse,
)
from questly.core.notifications.service import (
    NotificationNotFoundError,
    NotificationService,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def notification_service(request: Request) -> NotificationService:
    """Resolve NotificationService from application state."""
    return request.app.state.notification_service


def notification_response(
    notification: Notification,
) -> NotificationResponse:
    """Convert the domain model into an API response."""
    if notification.id is None:
        raise RuntimeError("persisted notification has no id")

    return NotificationResponse(
        id=notification.id,
        kind=notification.kind,
        payload=notification.payload,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(request: Request) -> NotificationListResponse:
    """List notifications belonging to the logged-in user."""
    actor = current_actor(request)
    items = notification_service(request).list_for_user(actor.user_id)

    return NotificationListResponse(
        items=[notification_response(item) for item in items]
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    request: Request,
    notification_id: int,
) -> NotificationResponse:
    """Mark one of the current user's notifications as read."""
    actor = current_actor(request)

    try:
        notification = notification_service(request).mark_read(
            actor.user_id,
            notification_id,
        )
    except NotificationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "notification_not_found",
                "message": "Notification not found",
            },
        ) from None

    return notification_response(notification)


@router.post("/read-all", response_model=MarkAllReadResponse)
def mark_all_notifications_read(request: Request) -> MarkAllReadResponse:
    """Mark all notifications belonging to the current user as read."""
    actor = current_actor(request)
    count = notification_service(request).mark_all_read(actor.user_id)

    return MarkAllReadResponse(updated_count=count)
