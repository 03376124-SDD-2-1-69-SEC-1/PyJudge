"""Tests for Assignment application rules."""

import pytest

from greader.core.assignments.models import Assignment, Difficulty, TestCase
from greader.core.assignments.service import AssignmentNotFoundError, AssignmentService
from tests.fakes.assignments import FakeAssignmentRepository


def test_title_only_patch_preserves_artifact_and_test_cases() -> None:
    repository = FakeAssignmentRepository()
    existing = repository.create(
        Assignment(
            title="Original title",
            problem_statement="Original problem",
            difficulty=Difficulty.MEDIUM,
            metadata={"key": "value"},
            artifact_id=42,
            test_cases=[TestCase(input_data="1", expected_output="1")],
        )
    )
    service = AssignmentService(repository)

    updated = service.patch(existing.id, title="New title")

    assert updated.title == "New title"
    assert updated.artifact_id == 42
    stored = repository.get(existing.id)
    assert stored is not None
    assert stored.test_cases == existing.test_cases


def test_replace_overwrites_every_client_writable_field() -> None:
    repository = FakeAssignmentRepository()
    service = AssignmentService(repository)
    created = service.create(
        title="Original title",
        problem_statement="Original problem",
        difficulty=Difficulty.EASY,
        metadata={"key": "value"},
    )

    replaced = service.replace(
        created.id,
        title="New title",
        problem_statement="New problem",
        difficulty=Difficulty.HARD,
        metadata={},
    )

    assert replaced.title == "New title"
    assert replaced.problem_statement == "New problem"
    assert replaced.difficulty == Difficulty.HARD
    assert replaced.metadata == {}


def test_create_and_list_assignments_use_repository_seam() -> None:
    service = AssignmentService(FakeAssignmentRepository())

    created = service.create(
        title="New assignment",
        problem_statement="Solve it",
        difficulty=Difficulty.EASY,
        metadata={"source": "test"},
    )

    assert service.list() == [created]


def test_get_missing_assignment_raises_not_found() -> None:
    service = AssignmentService(FakeAssignmentRepository())

    with pytest.raises(AssignmentNotFoundError):
        service.get(999)


def test_delete_assignment_uses_repository_seam() -> None:
    service = AssignmentService(FakeAssignmentRepository())
    created = service.create(
        title="New assignment",
        problem_statement="Solve it",
        difficulty=Difficulty.EASY,
    )

    service.delete(created.id)

    assert service.list() == []


def test_delete_missing_assignment_raises_not_found() -> None:
    """The service raises a domain error rather than returning a bool.

    Returning False would make the routes decide what a missing row means, and
    TopicService already raises — one convention, not two.
    """
    service = AssignmentService(FakeAssignmentRepository())

    with pytest.raises(AssignmentNotFoundError):
        service.delete(999)
