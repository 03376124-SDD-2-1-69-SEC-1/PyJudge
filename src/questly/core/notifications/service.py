"""Business logic for user notifications."""

from datetime import datetime
from typing import Protocol

from questly.core.notifications.models import Notification
from questly.core.notifications.ports import (
    EmailSender,
    NotificationRepository,
)


class NotificationNotFoundError(Exception):
    """Raised when a notification does not exist for the requested user."""


class Clock(Protocol):
    """Provide the current time."""

    def now(self) -> datetime:
        """Return the current time."""
        ...


class NotificationService:
    """Coordinate notification storage, read state, and email delivery."""

    def __init__(
        self,
        repository: NotificationRepository,
        email_sender: EmailSender,
        clock: Clock,
    ) -> None:
        self._repository = repository
        self._email_sender = email_sender
        self._clock = clock

    def list_for_user(self, user_id: int) -> list[Notification]:
        """List a user's notifications, newest first."""
        return self._repository.list_for_user(user_id)

    def mark_read(
        self,
        user_id: int,
        notification_id: int,
    ) -> Notification:
        """Mark a notification as read only if it belongs to the user."""
        notification = self._repository.get(notification_id)

        if notification is None or notification.user_id != user_id:
            raise NotificationNotFoundError

        if notification.read_at is not None:
            return notification

        return self._repository.mark_read(
            notification_id,
            read_at=self._clock.now(),
        )

    def mark_all_read(self, user_id: int) -> int:
        """Mark every unread notification belonging to the user as read."""
        return self._repository.mark_all_read(
            user_id,
            read_at=self._clock.now(),
        )

    def create(
        self,
        *,
        user_id: int,
        kind: str,
        payload: dict[str, str | int | bool | None],
    ) -> Notification:
        """Persist a notification for one user."""
        return self._repository.create(
            Notification(
                user_id=user_id,
                kind=kind,
                payload=payload,
                created_at=self._clock.now(),
            )
        )

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> None:
        """Send an email through the notification-owned email port."""
        self._email_sender.send(to=to, subject=subject, body=body)
