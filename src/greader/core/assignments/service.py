"""Assignment use cases independent from HTTP and database technology."""

from __future__ import annotations

from greader.core.assignments.models import Assignment, Difficulty, TestCase
from greader.core.assignments.ports import AssignmentRepository


class AssignmentNotFoundError(Exception):
    """Raised when a requested Assignment does not exist."""


class TestCaseNotFoundError(Exception):
    """Raised when a requested TestCase does not exist on its Assignment."""


class AssignmentService:
    """Coordinate Assignment use cases through a repository seam."""

    def __init__(self, repo: AssignmentRepository) -> None:
        """Initialize the service with an Assignment repository."""
        self._repo = repo

    def list(self) -> list[Assignment]:
        """Return every Assignment."""
        return self._repo.list()

    def get(self, assignment_id: int) -> Assignment:
        """Return one Assignment or raise when it does not exist."""
        assignment = self._repo.get(assignment_id)
        if assignment is None:
            raise AssignmentNotFoundError
        return assignment

    def create(
        self,
        title: str,
        problem_statement: str,
        difficulty: Difficulty,
        metadata: dict[str, object] | None = None,
    ) -> Assignment:
        """Create and persist an Assignment."""
        assignment = Assignment(
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            metadata=metadata if metadata is not None else {},
        )
        return self._repo.create(assignment)

    def replace(
        self,
        assignment_id: int,
        title: str,
        problem_statement: str,
        difficulty: Difficulty,
        metadata: dict[str, object],
    ) -> Assignment:
        """Replace every client-writable field of an Assignment.

        Test cases and `artifact_id` are not client-writable through this use
        case, so they are carried over from the stored entity.
        """
        existing = self.get(assignment_id)
        return self._repo.update(
            Assignment(
                id=assignment_id,
                title=title,
                problem_statement=problem_statement,
                difficulty=difficulty,
                metadata=metadata,
                artifact_id=existing.artifact_id,
                test_cases=existing.test_cases,
            )
        )

    def patch(
        self,
        assignment_id: int,
        title: str | None = None,
        problem_statement: str | None = None,
        difficulty: Difficulty | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Assignment:
        """Update supplied fields while retaining all omitted values."""
        existing = self.get(assignment_id)
        return self._repo.update(
            Assignment(
                id=assignment_id,
                title=title if title is not None else existing.title,
                problem_statement=problem_statement
                if problem_statement is not None
                else existing.problem_statement,
                difficulty=difficulty
                if difficulty is not None
                else existing.difficulty,
                metadata=metadata if metadata is not None else existing.metadata,
                artifact_id=existing.artifact_id,
                test_cases=existing.test_cases,
            )
        )

    def delete(self, assignment_id: int) -> None:
        """Delete an Assignment or raise when it does not exist."""
        if not self._repo.delete(assignment_id):
            raise AssignmentNotFoundError

    def add_test_case(
        self,
        assignment_id: int,
        input_data: str,
        expected_output: str,
        is_hidden: bool,
        order_index: int,
    ) -> TestCase:
        """Append a TestCase to an Assignment and persist the aggregate.

        The id comes from the repository, not from here: a service-side counter
        would disagree with the sequence the database uses and would reuse an id
        after a delete.
        """
        existing = self.get(assignment_id)
        new_test_case = TestCase(
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            order_index=order_index,
        )
        updated = self._save_test_cases(existing, [*existing.test_cases, new_test_case])

        known_ids = {test_case.id for test_case in existing.test_cases}
        # Exactly one test case must be new. Unpacking fails loudly if the
        # adapter returned anything else, instead of guessing which one it is.
        (added,) = [tc for tc in updated.test_cases if tc.id not in known_ids]
        return added

    def list_test_cases(self, assignment_id: int) -> list[TestCase]:
        """Return every TestCase belonging to an Assignment."""
        return self.get(assignment_id).test_cases

    def get_test_case(self, assignment_id: int, test_case_id: int) -> TestCase:
        """Return one TestCase or raise when it does not exist."""
        return self._find_test_case(self.get(assignment_id), test_case_id)

    def update_test_case(
        self,
        assignment_id: int,
        test_case_id: int,
        input_data: str | None = None,
        expected_output: str | None = None,
        is_hidden: bool | None = None,
        order_index: int | None = None,
    ) -> TestCase:
        """Update supplied TestCase fields while retaining omitted values."""
        existing_assignment = self.get(assignment_id)
        existing_test_case = self._find_test_case(existing_assignment, test_case_id)
        updated_test_case = TestCase(
            id=existing_test_case.id,
            input_data=input_data
            if input_data is not None
            else existing_test_case.input_data,
            expected_output=expected_output
            if expected_output is not None
            else existing_test_case.expected_output,
            is_hidden=is_hidden
            if is_hidden is not None
            else existing_test_case.is_hidden,
            order_index=order_index
            if order_index is not None
            else existing_test_case.order_index,
        )
        replacement = [
            updated_test_case if tc.id == test_case_id else tc
            for tc in existing_assignment.test_cases
        ]
        updated = self._save_test_cases(existing_assignment, replacement)
        return self._find_test_case(updated, test_case_id)

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> None:
        """Delete a TestCase or raise when it does not exist."""
        existing_assignment = self.get(assignment_id)
        remaining = [
            tc for tc in existing_assignment.test_cases if tc.id != test_case_id
        ]
        if len(remaining) == len(existing_assignment.test_cases):
            raise TestCaseNotFoundError
        self._save_test_cases(existing_assignment, remaining)

    def _find_test_case(self, assignment: Assignment, test_case_id: int) -> TestCase:
        for test_case in assignment.test_cases:
            if test_case.id == test_case_id:
                return test_case
        raise TestCaseNotFoundError

    def _save_test_cases(
        self, assignment: Assignment, test_cases: list[TestCase]
    ) -> Assignment:
        return self._repo.update(
            Assignment(
                id=assignment.id,
                title=assignment.title,
                problem_statement=assignment.problem_statement,
                difficulty=assignment.difficulty,
                metadata=assignment.metadata,
                artifact_id=assignment.artifact_id,
                test_cases=test_cases,
            )
        )
