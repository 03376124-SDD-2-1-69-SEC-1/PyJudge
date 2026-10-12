"""What the G-02a dropdown shows: rows built from stored and computed items."""

from dataclasses import dataclass
from datetime import datetime

from questly.core.notifications.models import (
    DueSoon,
    Notification,
    NotificationKind,
)

# The dropdown lists this many of the newest stored notifications.
MENU_SIZE = 8

_TITLES = {
    NotificationKind.ASSIGNMENT_PUBLISHED: "New problem: {title}",
    NotificationKind.ASSIGNMENT_UPDATED: "Problem updated: {title}",
    NotificationKind.ASSIGNMENT_NOTIFIED: "Reminder: {title}",
}


@dataclass(frozen=True, slots=True)
class NotificationRow:
    """One stored notification, worded for the dropdown."""

    id: int
    title: str
    detail: str
    href: str
    created_at: datetime
    unread: bool


@dataclass(frozen=True, slots=True)
class DueSoonRow:
    """One "Deadline tomorrow" item; computed, so it has no id and no read state."""

    title: str
    href: str
    deadline: datetime


@dataclass(frozen=True, slots=True)
class NotificationMenu:
    """The bell badge and the dropdown's two lists, due-soon first."""

    unread_count: int
    due_soon: tuple[DueSoonRow, ...]
    recent: tuple[NotificationRow, ...]
    # The local path the dropdown's forms send the user back to.
    return_to: str = "/"

    @property
    def is_empty(self) -> bool:
        return not self.due_soon and not self.recent


def _assignment_href(classroom_id: object, assignment_id: object) -> str:
    return f"/classes/{classroom_id}/assignments/{assignment_id}"


def describe(notification: Notification) -> NotificationRow:
    """Word one stored notification; the payload is what `notify_members` wrote."""
    if notification.id is None:
        raise RuntimeError("persisted notification has no id")
    payload = notification.payload
    return NotificationRow(
        id=notification.id,
        title=_TITLES[notification.kind].format(title=payload["title"]),
        detail=str(payload["reason"]) if "reason" in payload else "",
        href=_assignment_href(payload["classroom_id"], payload["assignment_id"]),
        created_at=notification.created_at,
        unread=notification.read_at is None,
    )


def build_menu(
    notifications: list[Notification],
    due_soon: list[DueSoon],
    return_to: str = "/",
) -> NotificationMenu:
    """`notifications` is newest first, as `NotificationService.list_for_user`."""
    return NotificationMenu(
        unread_count=sum(1 for item in notifications if item.read_at is None),
        due_soon=tuple(
            DueSoonRow(
                title=f"Deadline tomorrow: {item.title}",
                href=_assignment_href(item.classroom_id, item.assignment_id),
                deadline=item.deadline,
            )
            for item in due_soon
        ),
        recent=tuple(describe(item) for item in notifications[:MENU_SIZE]),
        return_to=return_to,
    )
