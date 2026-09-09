"""Assignment use cases independent from HTTP and database technology."""

from greader.core.assignments.models import Assignment, TestCase
from greader.core.assignments.repository import AssignmentRepository


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
        return self._repo.list_all()

    def get(self, assignment_id: int) -> Assignment:
        """Return one Assignment or raise when it does not exist."""
        assignment = self._repo.get_by_id(assignment_id)
        if assignment is None:
            raise AssignmentNotFoundError
        return assignment

    def create(
        self,
        title: str,
        problem_statement: str,
        difficulty: str,
        metadata: dict[str, object] | None = None,
    ) -> Assignment:
        """Create and persist an Assignment."""
        assignment = Assignment(
            id=None,
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            metadata=metadata if metadata is not None else {},
        )
        return self._repo.create(assignment)

    def update(
        self,
        assignment_id: int,
        title: str | None = None,
        problem_statement: str | None = None,
        difficulty: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> Assignment:
        """Update supplied fields while retaining all omitted values."""
        existing = self.get(assignment_id)
        updated_assignment = Assignment(
            id=assignment_id,
            title=title if title is not None else existing.title,
            problem_statement=problem_statement
            if problem_statement is not None
            else existing.problem_statement,
            difficulty=difficulty if difficulty is not None else existing.difficulty,
            metadata=metadata if metadata is not None else existing.metadata,
            artifact_id=existing.artifact_id,
            created_at=existing.created_at,
            updated_at=existing.updated_at,
            test_cases=existing.test_cases,
        )
        updated = self._repo.update(assignment_id, updated_assignment)
        if updated is None:
            raise AssignmentNotFoundError
        return updated

    def delete(self, assignment_id: int) -> bool:
        """Delete an Assignment and report whether it existed."""
        return self._repo.delete(assignment_id)

    def add_test_case(
        self,
        assignment_id: int,
        input_data: str,
        expected_output: str,
        is_hidden: bool,
        order_index: int,
    ) -> TestCase:
        """Append a TestCase to an Assignment and persist the aggregate."""
        existing = self.get(assignment_id)
        next_id = max((tc.id for tc in existing.test_cases if tc.id), default=0) + 1
        new_test_case = TestCase(
            id=next_id,
            assignment_id=assignment_id,
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            order_index=order_index,
        )
        self._save_test_cases(existing, [*existing.test_cases, new_test_case])
        return new_test_case

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
            assignment_id=assignment_id,
            input_data=input_data
            if input_data is not None
            else existing_test_case.input_data,
            expected_output=expected_output
            if expected_output is not None
            else existing_test_case.expected_output,
            is_hidden=is_hidden if is_hidden is not None else existing_test_case.is_hidden,
            order_index=order_index
            if order_index is not None
            else existing_test_case.order_index,
            created_at=existing_test_case.created_at,
            updated_at=existing_test_case.updated_at,
        )
        replacement = [
            updated_test_case if tc.id == test_case_id else tc
            for tc in existing_assignment.test_cases
        ]
        self._save_test_cases(existing_assignment, replacement)
        return updated_test_case

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool:
        """Delete a TestCase and report whether it existed."""
        existing_assignment = self.get(assignment_id)
        remaining = [
            tc for tc in existing_assignment.test_cases if tc.id != test_case_id
        ]
        if len(remaining) == len(existing_assignment.test_cases):
            return False
        self._save_test_cases(existing_assignment, remaining)
        return True

    def _find_test_case(self, assignment: Assignment, test_case_id: int) -> TestCase:
        for test_case in assignment.test_cases:
            if test_case.id == test_case_id:
                return test_case
        raise TestCaseNotFoundError

    def _save_test_cases(
        self, assignment: Assignment, test_cases: list[TestCase]
    ) -> None:
        updated_assignment = Assignment(
            id=assignment.id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=test_cases,
        )
        self._repo.update(assignment.id, updated_assignment)
