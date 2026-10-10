"""In-memory notification repository for tests."""

from dataclasses import replace
from datetime import datetime

from questly.core.notifications.models import Notification


class FakeNotificationRepository:
    """Store notifications in memory using the production repository contract."""

    def __init__(self) -> None:
        self._notifications: dict[int, Notification] = {}
        self._next_id = 1

    def list_for_user(self, user_id: int) -> list[Notification]:
        return sorted(
            (
                notification
                for notification in self._notifications.values()
                if notification.user_id == user_id
            ),
            key=lambda notification: (
                notification.created_at,
                notification.id or 0,
            ),
            reverse=True,
        )

    def get(self, notification_id: int) -> Notification | None:
        return self._notifications.get(notification_id)

    def create(self, notification: Notification) -> Notification:
        if notification.id is not None:
            raise ValueError("new notification must not already have an id")

        stored = replace(notification, id=self._next_id)
        self._notifications[self._next_id] = stored
        self._next_id += 1
        return stored

    def mark_read(
        self,
        notification_id: int,
        *,
        read_at: datetime,
    ) -> Notification:
        notification = self._notifications.get(notification_id)
        if notification is None:
            raise KeyError(notification_id)

        if notification.read_at is None:
            notification = replace(notification, read_at=read_at)
            self._notifications[notification_id] = notification

        return notification

    def mark_all_read(
        self,
        user_id: int,
        *,
        read_at: datetime,
    ) -> int:
        updated = 0

        for notification_id, notification in self._notifications.items():
            if notification.user_id != user_id or notification.read_at is not None:
                continue

            self._notifications[notification_id] = replace(
                notification,
                read_at=read_at,
            )
            updated += 1

        return updated
