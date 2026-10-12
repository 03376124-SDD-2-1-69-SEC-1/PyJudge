"""Domain model for user notifications (ADR-0007 §6)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

# Stored as JSONB in `core.notifications.payload`.
NotificationPayload = dict[str, str | int | bool | None]


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
    payload: NotificationPayload
    created_at: datetime
    id: int | None = None
    read_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DueSoon:
    """ "Deadline tomorrow": a Posting the Student has not submitted, due soon.

    Computed on read and never stored or emailed (ADR-0007 §6.2).
    """

    classroom_id: int
    assignment_id: int
    title: str
    deadline: datetime
