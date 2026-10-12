"""Domain model for user notifications (ADR-0007 §6)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class NotificationKind(StrEnum):
    """What a stored notification is about; `core.notifications.kind` holds it."""

    ASSIGNMENT_PUBLISHED = "assignment_published"
    ASSIGNMENT_UPDATED = "assignment_updated"
    ASSIGNMENT_NOTIFIED = "assignment_notified"


@dataclass(frozen=True, slots=True)
class Notification:
    """A notification belonging to one user."""

    user_id: int
    kind: NotificationKind
    payload: dict[str, str | int | bool | None]
    created_at: datetime
    id: int | None = None
    read_at: datetime | None = None
