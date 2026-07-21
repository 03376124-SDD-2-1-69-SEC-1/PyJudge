"""Assignment repository protocol and in-memory implementation."""

from typing import Protocol

from greader.assignments.models import Assignment


class AssignmentRepository(Protocol):
    """Interface for assignment persistence."""

    def list_assignments(self) -> list[Assignment]:
        """Return all assignments."""
        ...

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        """Return a single assignment by ID, or None if not found."""
        ...

    def save_assignment(self, assignment: Assignment) -> None:
        """Create or update an assignment."""
        ...


class InMemoryAssignmentRepository:
    """In-memory implementation of the assignment repository."""

    def __init__(self) -> None:
        self._store: dict[str, Assignment] = {}

    def list_assignments(self) -> list[Assignment]:
        """Return all assignments."""
        return list(self._store.values())

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        """Return a single assignment by ID, or None if not found."""
        return self._store.get(assignment_id)

    def save_assignment(self, assignment: Assignment) -> None:
        """Create or update an assignment."""
        self._store[assignment.id] = assignment
