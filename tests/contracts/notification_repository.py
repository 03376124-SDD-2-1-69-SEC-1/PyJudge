"""Contract every NotificationRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/notifications/` and to
`SQLNotificationRepository` in `tests/db/`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from questly.core.notifications.models import Notification, NotificationKind
from questly.core.notifications.ports import NotificationRepository
from tests.contracts.support import IdFactory, NeedsUsers

NOW = datetime(2026, 10, 10, 6, 0, tzinfo=UTC)


def notification(
    user_id: int,
    *,
    created_at: datetime = NOW,
    kind: NotificationKind = NotificationKind.ASSIGNMENT_PUBLISHED,
) -> Notification:
    return Notification(
        user_id=user_id,
        kind=kind,
        payload={"classroom_id": 3, "title": "Binary search", "late": False},
        created_at=created_at,
    )


class NotificationRepositoryContract(NeedsUsers):
    """Checks that hold for any store behind NotificationRepository."""

    def test_create_assigns_id_and_get_round_trips(
        self, repository: NotificationRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(
            notification(new_user(), kind=NotificationKind.ASSIGNMENT_UPDATED)
        )

        assert isinstance(created.id, int)
        assert created.read_at is None
        assert repository.get(created.id) == created
        assert repository.get(created.id).kind is NotificationKind.ASSIGNMENT_UPDATED
        assert repository.get(999_999) is None

    def test_list_for_user_is_newest_first_and_only_theirs(
        self, repository: NotificationRepository, new_user: IdFactory
    ) -> None:
        owner, other = new_user(), new_user()
        older = repository.create(notification(owner, created_at=NOW))
        newer = repository.create(
            notification(owner, created_at=NOW + timedelta(hours=1))
        )
        same_time = repository.create(
            notification(owner, created_at=NOW + timedelta(hours=1))
        )
        repository.create(notification(other))

        assert repository.list_for_user(owner) == [same_time, newer, older]
        assert repository.list_for_user(new_user()) == []

    def test_mark_read_sets_read_at(
        self, repository: NotificationRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(notification(new_user()))
        read_at = NOW + timedelta(minutes=5)

        marked = repository.mark_read(created.id, read_at=read_at)

        assert marked.read_at == read_at
        assert repository.get(created.id) == marked

    def test_mark_read_of_unknown_id_raises_key_error(
        self, repository: NotificationRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.mark_read(999_999, read_at=NOW)

    def test_mark_all_read_counts_and_touches_only_that_users_unread_rows(
        self, repository: NotificationRepository, new_user: IdFactory
    ) -> None:
        owner, other = new_user(), new_user()
        already_read = repository.create(notification(owner))
        repository.mark_read(already_read.id, read_at=NOW)
        unread = [repository.create(notification(owner)) for _ in range(2)]
        theirs = repository.create(notification(other))
        read_at = NOW + timedelta(hours=2)

        assert repository.mark_all_read(owner, read_at=read_at) == 2
        assert [repository.get(n.id).read_at for n in unread] == [read_at, read_at]
        assert repository.get(already_read.id).read_at == NOW
        assert repository.get(theirs.id).read_at is None
        assert repository.mark_all_read(owner, read_at=read_at) == 0
