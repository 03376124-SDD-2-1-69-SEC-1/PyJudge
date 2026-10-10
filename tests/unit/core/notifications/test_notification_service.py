"""Unit tests for NotificationService."""

from datetime import UTC, datetime

import pytest

from questly.core.notifications.models import Notification
from questly.core.notifications.service import (
    NotificationNotFoundError,
    NotificationService,
)
from tests.fakes.notifications import FakeNotificationRepository


class FixedClock:
    """Return a predictable time."""

    def now(self) -> datetime:
        return datetime(2026, 10, 10, 6, 0, tzinfo=UTC)


class FakeEmailSender:
    """Capture outgoing emails."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.messages.append({"to": to, "subject": subject, "body": body})


@pytest.fixture
def repository() -> FakeNotificationRepository:
    return FakeNotificationRepository()


@pytest.fixture
def service(
    repository: FakeNotificationRepository,
) -> NotificationService:
    return NotificationService(
        repository=repository,
        email_sender=FakeEmailSender(),
        clock=FixedClock(),
    )


def add_notification(
    repository: FakeNotificationRepository,
    *,
    user_id: int,
) -> Notification:
    return repository.create(
        Notification(
            user_id=user_id,
            kind="assignment_published",
            payload={"title": "Homework 1"},
            created_at=datetime(2026, 10, 10, 5, 0, tzinfo=UTC),
        )
    )


def test_list_for_user_returns_only_own_notifications(
    service: NotificationService,
    repository: FakeNotificationRepository,
) -> None:
    own = add_notification(repository, user_id=1)
    add_notification(repository, user_id=2)

    assert service.list_for_user(1) == [own]


def test_mark_read_marks_own_notification(
    service: NotificationService,
    repository: FakeNotificationRepository,
) -> None:
    notification = add_notification(repository, user_id=1)

    result = service.mark_read(1, notification.id or 0)

    assert result.read_at == FixedClock().now()


def test_mark_read_rejects_another_users_notification(
    service: NotificationService,
    repository: FakeNotificationRepository,
) -> None:
    notification = add_notification(repository, user_id=2)

    with pytest.raises(NotificationNotFoundError):
        service.mark_read(1, notification.id or 0)


def test_mark_all_read_only_affects_own_notifications(
    service: NotificationService,
    repository: FakeNotificationRepository,
) -> None:
    own = add_notification(repository, user_id=1)
    other = add_notification(repository, user_id=2)

    assert service.mark_all_read(1) == 1
    assert repository.get(own.id or 0).read_at == FixedClock().now()
    assert repository.get(other.id or 0).read_at is None


def test_create_uses_clock_time(
    service: NotificationService,
) -> None:
    result = service.create(
        user_id=1,
        kind="assignment_updated",
        payload={"title": "Homework 1", "reason": "Deadline changed"},
    )

    assert result.id is not None
    assert result.created_at == FixedClock().now()
    assert result.user_id == 1
    assert result.kind == "assignment_updated"
