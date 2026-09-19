"""Contract every AssignmentRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/assignments/` and to
`SQLAssignmentRepository` in `tests/db/`.
"""

from __future__ import annotations

import pytest

from greader.core.assignments.models import Assignment, Difficulty, TestCase
from greader.core.assignments.ports import AssignmentRepository


def assignment(
    title: str = "Title",
    problem_statement: str = "Statement",
    difficulty: Difficulty = Difficulty.EASY,
    metadata: dict[str, object] | None = None,
    test_cases: list[TestCase] | None = None,
) -> Assignment:
    """Return an unsaved Assignment for a contract check to hand to an adapter."""
    return Assignment(
        title=title,
        problem_statement=problem_statement,
        difficulty=difficulty,
        metadata=metadata if metadata is not None else {},
        test_cases=test_cases if test_cases is not None else [],
    )


class AssignmentRepositoryContract:
    """Checks that hold for any store behind AssignmentRepository."""

    def test_create_returns_entity_with_non_none_int_id(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(assignment())

        assert isinstance(created.id, int)

    def test_create_twice_returns_different_ids(
        self, repository: AssignmentRepository
    ) -> None:
        first = repository.create(assignment())
        second = repository.create(assignment())

        assert first.id != second.id

    def test_create_preserves_every_field_except_id(
        self, repository: AssignmentRepository
    ) -> None:
        submitted = assignment(
            title="Original title",
            problem_statement="Original statement",
            difficulty=Difficulty.HARD,
            metadata={"key": "value"},
        )

        created = repository.create(submitted)

        assert created.title == submitted.title
        assert created.problem_statement == submitted.problem_statement
        assert created.difficulty == submitted.difficulty
        assert created.metadata == submitted.metadata

    def test_get_after_create_returns_equal_entity(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(assignment())

        fetched = repository.get(created.id)

        assert fetched == created

    def test_get_on_unknown_id_returns_none_and_does_not_raise(
        self, repository: AssignmentRepository
    ) -> None:
        assert repository.get(999_999) is None

    def test_update_preserves_fields_absent_from_the_update(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(
            assignment(title="Original title", metadata={"key": "value"})
        )

        updated = repository.update(
            Assignment(
                id=created.id,
                title="New title",
                problem_statement=created.problem_statement,
                difficulty=created.difficulty,
                metadata=created.metadata,
                artifact_id=created.artifact_id,
                test_cases=created.test_cases,
            )
        )

        assert updated.title == "New title"
        assert updated.metadata == {"key": "value"}

    def test_delete_returns_true_once_then_false(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(assignment())

        assert repository.delete(created.id) is True
        assert repository.delete(created.id) is False

    def test_test_case_belongs_to_its_parent_by_containment_alone(
        self, repository: AssignmentRepository
    ) -> None:
        """A TestCase reached through its parent carries no separate pointer."""
        created = repository.create(
            assignment(test_cases=[TestCase(input_data="in", expected_output="out")])
        )

        fetched = repository.get(created.id)

        assert fetched is not None
        (test_case,) = fetched.test_cases
        assert test_case.input_data == "in"

    def test_create_assigns_ids_to_its_test_cases(
        self, repository: AssignmentRepository
    ) -> None:
        """Child ids come from the store, never from the caller or the service."""
        created = repository.create(
            assignment(
                test_cases=[
                    TestCase(input_data="1", expected_output="1"),
                    TestCase(input_data="2", expected_output="2", order_index=1),
                ]
            )
        )

        ids = [test_case.id for test_case in created.test_cases]
        assert all(isinstance(value, int) for value in ids)
        assert len(set(ids)) == 2

    def test_update_adds_a_test_case_without_an_id(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(
            assignment(test_cases=[TestCase(input_data="1", expected_output="1")])
        )

        updated = repository.update(
            Assignment(
                id=created.id,
                title=created.title,
                problem_statement=created.problem_statement,
                difficulty=created.difficulty,
                metadata=created.metadata,
                artifact_id=created.artifact_id,
                test_cases=[
                    *created.test_cases,
                    TestCase(input_data="2", expected_output="2", order_index=1),
                ],
            )
        )

        assert [tc.input_data for tc in updated.test_cases] == ["1", "2"]
        assert all(isinstance(tc.id, int) for tc in updated.test_cases)

    def test_update_deletes_a_test_case_left_out_of_the_aggregate(
        self, repository: AssignmentRepository
    ) -> None:
        created = repository.create(
            assignment(
                test_cases=[
                    TestCase(input_data="1", expected_output="1"),
                    TestCase(input_data="2", expected_output="2", order_index=1),
                ]
            )
        )
        kept, removed = created.test_cases

        updated = repository.update(
            Assignment(
                id=created.id,
                title=created.title,
                problem_statement=created.problem_statement,
                difficulty=created.difficulty,
                metadata=created.metadata,
                artifact_id=created.artifact_id,
                test_cases=[kept],
            )
        )

        assert [tc.id for tc in updated.test_cases] == [kept.id]
        assert removed.id not in {tc.id for tc in updated.test_cases}

    def test_update_on_unknown_id_raises_key_error(
        self, repository: AssignmentRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(
                Assignment(
                    id=999_999,
                    title="Ghost",
                    problem_statement="Statement",
                    difficulty=Difficulty.EASY,
                )
            )
