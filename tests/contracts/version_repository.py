"""Contract every VersionRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/assignments/` and to
`SQLVersionRepository` in `tests/db/`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from questly.core.assignments.models import (
    AssignmentVersion,
    Difficulty,
    JudgingSettings,
    TestCase,
    TestCaseKind,
)
from questly.core.assignments.ports import VersionRepository
from tests.contracts.support import IdFactory, NeedsAssignments

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def version(
    assignment_id: int, number: int, reason: str = "Published"
) -> AssignmentVersion:
    return AssignmentVersion(
        assignment_id=assignment_id,
        number=number,
        title="Binary search",
        problem_statement="Find x in a sorted list.",
        difficulty=Difficulty.MEDIUM,
        settings=JudgingSettings(time_limit_ms=2000, show_hidden_names=True),
        reason=reason,
        changed_at=NOW,
        test_cases=[
            TestCase("1 2", "3", kind=TestCaseKind.SAMPLE, id=10),
            TestCase(
                "9", "9", kind=TestCaseKind.EDGE, note="one item", order_index=1, id=11
            ),
        ],
    )


class VersionRepositoryContract(NeedsAssignments):
    """Checks that hold for any store behind VersionRepository."""

    def test_append_assigns_id_and_round_trips_the_snapshot(
        self, repository: VersionRepository, new_assignment: IdFactory
    ) -> None:
        assignment_id = new_assignment()
        created = repository.append(version(assignment_id, 1))

        assert isinstance(created.id, int)
        assert repository.get(assignment_id, 1) == created

    def test_get_on_unknown_number_returns_none(
        self, repository: VersionRepository, new_assignment: IdFactory
    ) -> None:
        assignment_id = new_assignment()
        repository.append(version(assignment_id, 1))

        assert repository.get(assignment_id, 2) is None

    def test_list_for_returns_that_assignment_in_append_order(
        self, repository: VersionRepository, new_assignment: IdFactory
    ) -> None:
        mine, other = new_assignment(), new_assignment()
        first = repository.append(version(mine, 1))
        repository.append(version(other, 1))
        second = repository.append(version(mine, 2, reason="Fixed a test"))

        assert repository.list_for(mine) == [first, second]

    def test_a_number_is_used_once_per_assignment(
        self, repository: VersionRepository, new_assignment: IdFactory
    ) -> None:
        assignment_id = new_assignment()
        repository.append(version(assignment_id, 1))

        with pytest.raises(ValueError):
            repository.append(version(assignment_id, 1))
