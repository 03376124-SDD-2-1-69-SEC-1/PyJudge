"""In-memory Assignment, Version and Posting repositories plus PostingStats."""

from __future__ import annotations

from dataclasses import replace

from greader.core.assignments.models import (
    Assignment,
    AssignmentVersion,
    Posting,
    PostingSummary,
    StudentStanding,
    TestCase,
)


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


class FakeVersionRepository:
    def __init__(self) -> None:
        self._items: list[AssignmentVersion] = []

    def append(self, version: AssignmentVersion) -> AssignmentVersion:
        if self.get(version.assignment_id, version.number) is not None:
            raise ValueError("version numbers are unique per assignment")
        created = replace(version, id=len(self._items) + 1)
        self._items.append(created)
        return created

    def list_for(self, assignment_id: int) -> list[AssignmentVersion]:
        return [v for v in self._items if v.assignment_id == assignment_id]

    def get(self, assignment_id: int, number: int) -> AssignmentVersion | None:
        for version in self._items:
            if (version.assignment_id, version.number) == (assignment_id, number):
                return version
        return None


class FakePostingRepository:
    def __init__(self) -> None:
        self._items: dict[int, Posting] = {}
        self._next_id = 1

    def create(self, posting: Posting) -> Posting:
        if self.find(posting.classroom_id, posting.assignment_id) is not None:
            raise ValueError("an assignment is posted once per classroom")
        created = replace(posting, id=self._next_id)
        self._next_id += 1
        self._items[created.id] = created
        return created

    def update(self, posting: Posting) -> Posting:
        self._items[posting.id]  # KeyError for an unknown id
        self._items[posting.id] = posting
        return posting

    def delete(self, posting_id: int) -> bool:
        return self._items.pop(posting_id, None) is not None

    def find(self, classroom_id: int, assignment_id: int) -> Posting | None:
        for posting in self._items.values():
            if (posting.classroom_id, posting.assignment_id) == (
                classroom_id,
                assignment_id,
            ):
                return posting
        return None

    def list_for_classroom(self, classroom_id: int) -> list[Posting]:
        return [
            self._items[key]
            for key in sorted(self._items)
            if self._items[key].classroom_id == classroom_id
        ]

    def list_for_assignment(self, assignment_id: int) -> list[Posting]:
        return [
            self._items[key]
            for key in sorted(self._items)
            if self._items[key].assignment_id == assignment_id
        ]


class FakePostingStats:
    """Zero/empty unless a test or the demo seed sets a value."""

    def __init__(self) -> None:
        self.summaries: dict[int, PostingSummary] = {}
        self.standings: dict[tuple[int, int], StudentStanding] = {}
        self.fail_rates: dict[int, float] = {}

    def posting_summary(self, posting_id: int) -> PostingSummary:
        if posting_id in self.summaries:
            return self.summaries[posting_id]
        return PostingSummary()

    def standing(self, posting_id: int, student_id: int) -> StudentStanding:
        if (posting_id, student_id) in self.standings:
            return self.standings[(posting_id, student_id)]
        return StudentStanding()

    def score(self, posting_id: int, student_id: int) -> float | None:
        return self.standing(posting_id, student_id).score

    def fail_rate(self, posting_id: int) -> float | None:
        if posting_id in self.fail_rates:
            return self.fail_rates[posting_id]
        return None
