import pytest

from greader.core.assignments.models import Assignment, TestCase
from greader.core.assignments.repository import InMemoryAssignmentRepository
from greader.core.assignments.service import AssignmentNotFoundError, AssignmentService


def test_title_only_update_preserves_artifact_and_test_cases() -> None:
    repository = InMemoryAssignmentRepository()
    existing = repository.create(
        Assignment(
            id=None,
            title="Original title",
            problem_statement="Original problem",
            difficulty="medium",
            metadata={"key": "value"},
            artifact_id=42,
            test_cases=[
                TestCase(
                    id=1,
                    input_data="1",
                    expected_output="1",
                )
            ],
        )
    )
    service = AssignmentService(repository)

    updated = service.update(existing.id or 0, title="New title")

    assert updated.title == "New title"
    assert updated.artifact_id == 42
    stored = repository.get(existing.id or 0)
    assert stored is not None
    assert stored.test_cases == existing.test_cases


def test_create_and_list_assignments_use_repository_seam() -> None:
    service = AssignmentService(InMemoryAssignmentRepository())

    created = service.create(
        title="New assignment",
        problem_statement="Solve it",
        difficulty="easy",
        metadata={"source": "test"},
    )

    assert service.list() == [created]


def test_get_missing_assignment_raises_not_found() -> None:
    service = AssignmentService(InMemoryAssignmentRepository())

    with pytest.raises(AssignmentNotFoundError):
        service.get(999)


def test_delete_assignment_uses_repository_seam() -> None:
    repository = InMemoryAssignmentRepository()
    service = AssignmentService(repository)
    created = service.create(
        title="New assignment",
        problem_statement="Solve it",
        difficulty="easy",
    )

    assert service.delete(created.id or 0) is True
    assert service.list() == []
    assert service.delete(created.id or 0) is False
