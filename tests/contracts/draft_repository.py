"""Contract every DraftRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/generation/` and to
`SQLDraftRepository` in `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from questly.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    JudgingSettings,
    TestCase,
    TestCaseKind,
)
from questly.core.generation.models import (
    Citation,
    Draft,
    DraftSettings,
    DraftStatus,
)
from questly.core.generation.ports import DraftRepository
from tests.contracts.support import IdFactory, NeedsAssignments, NeedsTopics

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def draft(classroom_id: int, requested_by: int, **changes: object) -> Draft:
    base = Draft(
        classroom_id=classroom_id,
        requested_by=requested_by,
        prompt="Binary search on a sorted list",
        content=AssignmentContent(
            title="Binary search",
            problem_statement="Find x.",
            difficulty=Difficulty.MEDIUM,
            test_cases=[
                TestCase("1 2 3\n2", "1", kind=TestCaseKind.SAMPLE),
                TestCase(
                    "1\n5", "-1", kind=TestCaseKind.EDGE, note="absent", order_index=1
                ),
            ],
            settings=JudgingSettings(time_limit_ms=1500),
        ),
        generated_at=NOW,
        citations=[Citation(7, 3, 12, 0.91, "a sorted array ...")],
        document_ids=[3, 4],
        classroom_ids=[classroom_id],
    )
    return replace(base, **changes)


class DraftRepositoryContract(NeedsAssignments, NeedsTopics):
    """Checks that hold for any store behind DraftRepository."""

    def test_create_assigns_id_and_round_trips_everything(
        self,
        repository: DraftRepository,
        new_classroom: IdFactory,
        new_user: IdFactory,
        new_topic: IdFactory,
    ) -> None:
        room = new_classroom()
        submitted = draft(room, new_user())
        submitted = replace(
            submitted,
            content=replace(submitted.content, topic_id=new_topic()),
            settings=DraftSettings(
                deadline=NOW + timedelta(days=7), max_score=20, allow_late=True
            ),
            citations=[
                Citation(7, 3, 12, 0.91, "a sorted array ..."),
                Citation(8, 3, None, 0.5, "no page"),
            ],
        )

        created = repository.create(submitted)

        assert isinstance(created.id, int)
        assert repository.get(created.id) == created
        assert created == replace(submitted, id=created.id)

    def test_get_on_unknown_id_returns_none(self, repository: DraftRepository) -> None:
        assert repository.get(999_999) is None

    def test_update_publishes(
        self,
        repository: DraftRepository,
        new_classroom: IdFactory,
        new_user: IdFactory,
        new_assignment: IdFactory,
    ) -> None:
        room, other = new_classroom(), new_classroom()
        created = repository.create(draft(room, new_user()))
        published = replace(
            created,
            status=DraftStatus.PUBLISHED,
            assignment_id=new_assignment(),
            classroom_ids=[room, other],
        )

        assert repository.update(published) == published
        assert repository.get(created.id) == published

    def test_update_on_unknown_id_raises_key_error(
        self, repository: DraftRepository, new_classroom: IdFactory, new_user: IdFactory
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(draft(new_classroom(), new_user(), id=999_999))

    def test_delete_returns_true_once_then_false(
        self, repository: DraftRepository, new_classroom: IdFactory, new_user: IdFactory
    ) -> None:
        created = repository.create(draft(new_classroom(), new_user()))

        assert repository.delete(created.id) is True
        assert repository.delete(created.id) is False

    def test_list_for_classroom_filters_on_its_own_classroom_in_id_order(
        self, repository: DraftRepository, new_classroom: IdFactory, new_user: IdFactory
    ) -> None:
        room, other = new_classroom(), new_classroom()
        author = new_user()
        first = repository.create(draft(room, author))
        repository.create(draft(other, author, classroom_ids=[other, room]))
        second = repository.create(draft(room, author))

        assert repository.list_for_classroom(room) == [first, second]

    def test_generations_are_counted_per_user_from_since_inclusive(
        self, repository: DraftRepository, new_user: IdFactory
    ) -> None:
        alice, bob = new_user(), new_user()
        midnight = NOW.replace(hour=0)
        repository.record_generation(alice, midnight - timedelta(seconds=1))
        repository.record_generation(alice, midnight)
        repository.record_generation(alice, NOW)
        repository.record_generation(bob, NOW)

        assert repository.count_generations(alice, midnight) == 2
        assert repository.count_generations(bob, midnight) == 1
        assert repository.count_generations(alice, NOW + timedelta(seconds=1)) == 0
