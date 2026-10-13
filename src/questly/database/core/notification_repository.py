"""SQL adapter for the NotificationRepository port (OPS-21)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import update
from sqlmodel import col, select

from questly.core.notifications.models import Notification, NotificationKind
from questly.database.core.tables import Notification as NotificationRow
from questly.database.session import SessionFactory


def _notification(row: NotificationRow) -> Notification:
    return Notification(
        id=row.id,
        user_id=row.user_id,
        kind=NotificationKind(row.kind),
        payload=dict(row.payload),
        created_at=row.created_at,
        read_at=row.read_at,
    )


class SQLNotificationRepository:
    """Store notifications in `core.notifications`."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def list_for_user(self, user_id: int) -> list[Notification]:
        """Return one user's notifications, newest first."""
        with self._session_factory() as db:
            rows = db.exec(
                select(NotificationRow)
                .where(NotificationRow.user_id == user_id)
                .order_by(
                    col(NotificationRow.created_at).desc(),
                    col(NotificationRow.id).desc(),
                )
            ).all()
            return [_notification(row) for row in rows]

    def get(self, notification_id: int) -> Notification | None:
        """Return one notification, if it exists."""
        with self._session_factory() as db:
            row = db.get(NotificationRow, notification_id)
            if row is None:
                return None
            return _notification(row)

    def create(self, notification: Notification) -> Notification:
        """Insert a notification and return it with its id."""
        with self._session_factory() as db:
            row = NotificationRow(
                user_id=notification.user_id,
                kind=notification.kind.value,
                payload=notification.payload,
                created_at=notification.created_at,
                read_at=notification.read_at,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _notification(row)

    def mark_read(self, notification_id: int, *, read_at: datetime) -> Notification:
        """Stamp `read_at` once; KeyError when the id is unknown."""
        with self._session_factory() as db:
            row = db.get(NotificationRow, notification_id)
            if row is None:
                raise KeyError(notification_id)
            if row.read_at is None:
                row.read_at = read_at
                db.commit()
                db.refresh(row)
            return _notification(row)

    def mark_all_read(self, user_id: int, *, read_at: datetime) -> int:
        """Stamp every unread notification of one user; return how many."""
        with self._session_factory() as db:
            result = db.exec(
                update(NotificationRow)
                .where(
                    col(NotificationRow.user_id) == user_id,
                    col(NotificationRow.read_at).is_(None),
                )
                .values(read_at=read_at)
            )
            db.commit()
            return result.rowcount
