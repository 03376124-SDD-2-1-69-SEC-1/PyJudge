"""Contract every AssignmentRepository implementation must satisfy.

CORE-10 adds the SQL adapter to `REPOSITORY_FACTORIES` and inherits every
check here for free.
"""

from collections.abc import Callable

import pytest

from greader.core.assignments.models import Assignment, TestCase
from greader.core.assignments.repository import (
    AssignmentRepository,
    InMemoryAssignmentRepository,
)

REPOSITORY_FACTORIES: list[Callable[[], AssignmentRepository]] = [
    InMemoryAssignmentRepository,
]


def _assignment(
    title: str = "Title",
    problem_statement: str = "Statement",
    difficulty: str = "easy",
    metadata: dict[str, object] | None = None,
    test_cases: list[TestCase] | None = None,
) -> Assignment:
    return Assignment(
        title=title,
        problem_statement=problem_statement,
        difficulty=difficulty,
        metadata=metadata if metadata is not None else {},
        test_cases=test_cases if test_cases is not None else [],
    )


@pytest.fixture(params=REPOSITORY_FACTORIES)
def repository(request: pytest.FixtureRequest) -> AssignmentRepository:
    return request.param()


def test_create_returns_entity_with_non_none_int_id(
    repository: AssignmentRepository,
) -> None:
    created = repository.create(_assignment())

    assert isinstance(created.id, int)


def test_create_twice_returns_different_ids(repository: AssignmentRepository) -> None:
    first = repository.create(_assignment())
    second = repository.create(_assignment())

    assert first.id != second.id


def test_create_preserves_every_field_except_id(
    repository: AssignmentRepository,
) -> None:
    submitted = _assignment(
        title="Original title",
        problem_statement="Original statement",
        difficulty="hard",
        metadata={"key": "value"},
    )

    created = repository.create(submitted)

    assert created.title == submitted.title
    assert created.problem_statement == submitted.problem_statement
    assert created.difficulty == submitted.difficulty
    assert created.metadata == submitted.metadata


def test_get_after_create_returns_equal_entity(
    repository: AssignmentRepository,
) -> None:
    created = repository.create(_assignment())

    fetched = repository.get(created.id)

    assert fetched == created


def test_get_on_unknown_id_returns_none_and_does_not_raise(
    repository: AssignmentRepository,
) -> None:
    assert repository.get(999_999) is None


def test_update_preserves_fields_absent_from_the_update(
    repository: AssignmentRepository,
) -> None:
    created = repository.create(
        _assignment(title="Original title", metadata={"key": "value"})
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


def test_delete_returns_true_once_then_false(repository: AssignmentRepository) -> None:
    created = repository.create(_assignment())

    assert repository.delete(created.id) is True
    assert repository.delete(created.id) is False


def test_test_case_belongs_to_its_parent_by_containment_alone(
    repository: AssignmentRepository,
) -> None:
    """A TestCase reached through its parent carries no separate parent pointer."""
    created = repository.create(
        _assignment(test_cases=[TestCase(id=1, input_data="in", expected_output="out")])
    )

    fetched = repository.get(created.id)

    assert fetched is not None
    (test_case,) = fetched.test_cases
    assert test_case.input_data == "in"
    assert not hasattr(test_case, "assignment_id")
