"""In-memory AssignmentRepository, behaviour-matched to the SQL adapter."""

from __future__ import annotations

from dataclasses import replace

from greader.core.assignments.models import Assignment, TestCase


def _ordered(test_cases: list[TestCase]) -> list[TestCase]:
    """Order children the way `SQLAssignmentRepository` reads them back."""
    return sorted(test_cases, key=lambda child: (child.order_index, child.id))


class FakeAssignmentRepository:
    """Store Assignments in process for tests and local experiments."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._items: dict[int, Assignment] = {}
        self._next_id = 1
        self._next_test_case_id = 1

    def list(self) -> list[Assignment]:
        """Return all stored Assignments, oldest first."""
        return [self._items[key] for key in sorted(self._items)]

    def get(self, assignment_id: int) -> Assignment | None:
        """Return an Assignment by id when present."""
        return self._items.get(assignment_id)

    def create(self, assignment: Assignment) -> Assignment:
        """Store and return an Assignment with generated ids."""
        new_id = self._next_id
        self._next_id += 1
        created = replace(
            assignment,
            id=new_id,
            test_cases=_ordered(self._assign_child_ids(assignment.test_cases)),
        )
        self._items[new_id] = created
        return created

    def update(self, assignment: Assignment) -> Assignment:
        """Replace an existing Assignment and return the stored value.

        Raises KeyError for an unknown id, like the SQL adapter: the Protocol
        says `update` takes an Assignment that already has its id.
        """
        existing = self._items[assignment.id]
        updated = replace(
            assignment,
            id=existing.id,
            test_cases=_ordered(self._assign_child_ids(assignment.test_cases)),
        )
        self._items[existing.id] = updated
        return updated

    def delete(self, assignment_id: int) -> bool:
        """Delete an Assignment and report whether it existed."""
        if assignment_id not in self._items:
            return False
        del self._items[assignment_id]
        return True

    def _assign_child_ids(self, test_cases: list[TestCase]) -> list[TestCase]:
        assigned = []
        for test_case in test_cases:
            if test_case.id is None:
                assigned.append(replace(test_case, id=self._next_test_case_id))
                self._next_test_case_id += 1
                continue
            assigned.append(test_case)
        return assigned
