"""Repository and email ports for Notifications."""

from datetime import datetime
from typing import Protocol

from questly.core.notifications.models import Notification


class NotificationRepository(Protocol):
    """Persistence operations required by NotificationService."""

    def list_for_user(self, user_id: int) -> list[Notification]:
        """Return notifications belonging to one user."""
        ...

    def get(self, notification_id: int) -> Notification | None:
        """Return one notification if it exists."""
        ...

    def create(self, notification: Notification) -> Notification:
        """Store a notification and assign its id."""
        ...

    def mark_read(
        self,
        notification_id: int,
        *,
        read_at: datetime,
    ) -> Notification:
        """Mark an existing notification as read."""
        ...

    def mark_all_read(
        self,
        user_id: int,
        *,
        read_at: datetime,
    ) -> int:
        """Mark all unread notifications for a user as read."""
        ...


class EmailSender(Protocol):
    """Port for sending email without coupling Core to an email provider."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Send an email message."""
        ...
