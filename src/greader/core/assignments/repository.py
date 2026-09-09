"""Repository port and in-memory Assignment adapter."""

from __future__ import annotations

from typing import Protocol

from greader.core.assignments.models import Assignment


class AssignmentRepository(Protocol):
    """Persistence operations required by AssignmentService.

    `create` is the only operation allowed to assign an id: it takes an
    Assignment whose `id` is `None` and returns one whose `id` is a real
    int. Every other operation, including `update`, takes and returns an
    Assignment that already has its id. Callers must always use the
    returned object, never the one they passed in.
    """

    def list(self) -> list[Assignment]: ...

    def get(self, assignment_id: int) -> Assignment | None: ...

    def create(self, assignment: Assignment) -> Assignment: ...

    def update(self, assignment: Assignment) -> Assignment: ...

    def delete(self, assignment_id: int) -> bool: ...


class InMemoryAssignmentRepository:
    """Store Assignments in process for tests and local development."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._items: dict[int, Assignment] = {}
        self._next_id: int = 1

    def list(self) -> list[Assignment]:
        """Return all stored Assignments."""
        return list(self._items.values())

    def get(self, assignment_id: int) -> Assignment | None:
        """Return an Assignment by id when present."""
        return self._items.get(assignment_id)

    def create(self, assignment: Assignment) -> Assignment:
        """Store and return an Assignment with a generated id."""
        new_id = self._next_id
        self._next_id += 1
        created = Assignment(
            id=new_id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            test_cases=assignment.test_cases,
        )
        self._items[new_id] = created
        return created

    def update(self, assignment: Assignment) -> Assignment:
        """Replace an existing Assignment and return the stored value."""
        existing = self._items[assignment.id]
        updated = Assignment(
            id=existing.id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            test_cases=assignment.test_cases,
        )
        self._items[existing.id] = updated
        return updated

    def delete(self, assignment_id: int) -> bool:
        """Delete an Assignment and report whether it existed."""
        if assignment_id not in self._items:
            return False
        del self._items[assignment_id]
        return True
