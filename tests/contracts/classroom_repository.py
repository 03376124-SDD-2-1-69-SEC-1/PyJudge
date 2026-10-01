"""Contract every ClassroomRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/classrooms/` and to
`SQLClassroomRepository` in `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from questly.core.classrooms.models import Classroom, Membership
from questly.core.classrooms.ports import ClassroomRepository
from tests.contracts.support import IdFactory, NeedsUsers

NOW = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)


def classroom(instructor_id: int, **changes: object) -> Classroom:
    base = Classroom(
        instructor_id=instructor_id,
        course_code="01076001",
        course_name="Programming Fundamentals",
        section="1",
        semester="1/2569",
        join_code="ABC123",
    )
    return replace(base, **changes)


class ClassroomRepositoryContract(NeedsUsers):
    """Checks that hold for any store behind ClassroomRepository."""

    def test_create_assigns_id_and_round_trips(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(classroom(new_user()))

        assert isinstance(created.id, int)
        assert repository.get(created.id) == created

    def test_get_on_unknown_id_returns_none(
        self, repository: ClassroomRepository
    ) -> None:
        assert repository.get(999_999) is None

    def test_list_owned_by_returns_only_that_instructor_in_id_order(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        mine, theirs = new_user(), new_user()
        first = repository.create(classroom(mine, join_code="AAA111"))
        repository.create(classroom(theirs, join_code="BBB222"))
        second = repository.create(classroom(mine, join_code="CCC333"))

        assert repository.list_owned_by(mine) == [first, second]

    def test_find_by_join_code(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(classroom(new_user(), join_code="XYZ789"))

        assert repository.find_by_join_code("XYZ789") == created
        assert repository.find_by_join_code("NOPE00") is None

    def test_update_replaces_values_including_archive_and_code(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(classroom(new_user()))
        changed = replace(
            created, course_name="Data Structures", archived=True, join_code=None
        )

        assert repository.update(changed) == changed
        assert repository.get(created.id) == changed
        assert repository.update(replace(changed, archived=False)).archived is False

    def test_update_on_unknown_id_raises_key_error(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(classroom(new_user(), id=999_999))

    def test_memberships_round_trip_in_id_order(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        room = repository.create(classroom(new_user()))
        alice, bob = new_user(), new_user()
        first = repository.add_membership(Membership(room.id, alice, NOW))
        second = repository.add_membership(Membership(room.id, bob, NOW))

        assert isinstance(first.id, int)
        assert repository.get_membership(room.id, alice) == first
        assert repository.get_membership(room.id, 999_999) is None
        assert repository.list_memberships(room.id) == [first, second]

    def test_list_joined_by_returns_classrooms_in_id_order(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        owner, student = new_user(), new_user()
        first = repository.create(classroom(owner, join_code="AAA111"))
        repository.create(classroom(owner, join_code="BBB222"))
        third = repository.create(classroom(owner, join_code="CCC333"))
        repository.add_membership(Membership(third.id, student, NOW))
        repository.add_membership(Membership(first.id, student, NOW))

        assert repository.list_joined_by(student) == [first, third]

    def test_remove_membership_reports_whether_it_existed(
        self, repository: ClassroomRepository, new_user: IdFactory
    ) -> None:
        room = repository.create(classroom(new_user()))
        student = new_user()
        repository.add_membership(Membership(room.id, student, NOW))

        assert repository.remove_membership(room.id, student) is True
        assert repository.remove_membership(room.id, student) is False
        assert repository.get_membership(room.id, student) is None
