"""API response schemas for Notifications."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """One notification returned to its owner."""

    model_config = ConfigDict(frozen=True)

    id: int
    kind: str
    payload: dict[str, str | int | bool | None]
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    """Notifications belonging to the current user."""

    items: list[NotificationResponse]


class MarkAllReadResponse(BaseModel):
    """Number of notifications marked as read."""

    updated_count: int = Field(ge=0)
