"""Contract every PostingRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/assignments/` and to
`SQLPostingRepository` in `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from questly.core.assignments.models import Posting, Schedule
from questly.core.assignments.ports import PostingRepository
from tests.contracts.support import IdFactory, NeedsAssignments

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def posting(classroom_id: int, assignment_id: int) -> Posting:
    return Posting(
        classroom_id=classroom_id,
        assignment_id=assignment_id,
        schedule=Schedule(
            deadline=NOW + timedelta(days=7),
            max_score=20,
            allow_late=True,
            allow_resubmission=False,
        ),
        published_at=NOW,
    )


class PostingRepositoryContract(NeedsAssignments):
    """Checks that hold for any store behind PostingRepository."""

    def test_create_assigns_id_and_find_round_trips(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        room, problem = new_classroom(), new_assignment()
        created = repository.create(posting(room, problem))

        assert isinstance(created.id, int)
        assert repository.find(room, problem) == created
        assert repository.find(room, 999_999) is None

    def test_an_assignment_is_posted_once_per_classroom(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        room, problem = new_classroom(), new_assignment()
        repository.create(posting(room, problem))

        with pytest.raises(ValueError):
            repository.create(posting(room, problem))

    def test_update_replaces_schedule_and_closing(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        created = repository.create(posting(new_classroom(), new_assignment()))
        changed = replace(
            created,
            schedule=Schedule(deadline=NOW + timedelta(days=1), max_score=5),
            closed_at=NOW + timedelta(hours=1),
        )

        assert repository.update(changed) == changed
        assert repository.find(created.classroom_id, created.assignment_id) == changed

    def test_update_on_unknown_id_raises_key_error(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(
                replace(posting(new_classroom(), new_assignment()), id=999_999)
            )

    def test_delete_returns_true_once_then_false(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        created = repository.create(posting(new_classroom(), new_assignment()))

        assert repository.delete(created.id) is True
        assert repository.delete(created.id) is False

    def test_lists_are_filtered_and_in_id_order(
        self,
        repository: PostingRepository,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        room_a, room_b = new_classroom(), new_classroom()
        one, two = new_assignment(), new_assignment()
        a1 = repository.create(posting(room_a, one))
        b1 = repository.create(posting(room_b, one))
        a2 = repository.create(posting(room_a, two))

        assert repository.list_for_classroom(room_a) == [a1, a2]
        assert repository.list_for_assignment(one) == [a1, b1]
