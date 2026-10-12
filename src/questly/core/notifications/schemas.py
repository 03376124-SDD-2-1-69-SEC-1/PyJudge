"""API response schemas for Notifications."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from questly.core.notifications.models import NotificationKind


class NotificationResponse(BaseModel):
    """One notification returned to its owner."""

    model_config = ConfigDict(frozen=True)

    id: int
    kind: NotificationKind
    payload: dict[str, str | int | bool | None]
    created_at: datetime
    read_at: datetime | None


class DueSoonResponse(BaseModel):
    """A Posting due within 24 h that the Student has not submitted."""

    model_config = ConfigDict(frozen=True)

    classroom_id: int
    assignment_id: int
    title: str
    deadline: datetime


class NotificationListResponse(BaseModel):
    """Notifications belonging to the current user, plus "Deadline tomorrow"."""

    items: list[NotificationResponse]
    due_soon: list[DueSoonResponse]


class MarkAllReadResponse(BaseModel):
    """Number of notifications marked as read."""

    updated_count: int = Field(ge=0)
