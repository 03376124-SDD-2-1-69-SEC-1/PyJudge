from greader.core.test_cases.models import TestCase
from greader.core.test_cases.repository import TestCaseRepository


class TestCaseNotFoundError(Exception):
    """Raised when a requested Test Case does not exist."""


class TestCaseService:
    """Coordinate Test Case use cases through a repository seam."""

    def __init__(self, repo: TestCaseRepository) -> None:
        """Initialize the service with a Test Case repository."""
        self._repo = repo

    def create_test_case(
        self,
        assignment_id: int,
        input_data: str,
        expected_output: str,
        is_hidden: bool,
        order_index: int,
    ) -> TestCase:
        """Create and persist a Test Case."""
        tc = TestCase(
            id=None,
            assignment_id=assignment_id,
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            order_index=order_index,
        )
        return self._repo.create_test_case(tc)

    def list_test_cases(self, assignment_id: int) -> list[TestCase]:
        """List Test Cases belonging to an Assignment."""
        test_cases = self._repo.list_test_cases(assignment_id)
        return test_cases

    def get_test_case(
        self, assignment_id: int, test_case_id: int
    ) -> TestCase:
        """Return a Test Case or raise TestCaseNotFoundError."""
        tc = self._repo.get_test_case(assignment_id, test_case_id)
        if tc is None:
            raise TestCaseNotFoundError
        return tc

    def update_test_case(
        self,
        assignment_id: int,
        test_case_id: int,
        input_data: str | None = None,
        expected_output: str | None = None,
        is_hidden: bool | None = None,
        order_index: int | None = None,
    ) -> TestCase:
        """Merge supplied fields into an existing Test Case."""
        existing = self.get_test_case(assignment_id, test_case_id)

        updated_tc = TestCase(
            id=test_case_id,
            assignment_id=assignment_id,
            input_data=input_data if input_data is not None else existing.input_data,
            expected_output=expected_output
            if expected_output is not None
            else existing.expected_output,
            is_hidden=is_hidden if is_hidden is not None else existing.is_hidden,
            order_index=order_index
            if order_index is not None
            else existing.order_index,
        )
        updated = self._repo.update_test_case(assignment_id, test_case_id, updated_tc)
        if updated is None:
            raise TestCaseNotFoundError
        return updated

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> None:
        """Delete a Test Case or raise TestCaseNotFoundError."""
        if not self._repo.delete_test_case(assignment_id, test_case_id):
            raise TestCaseNotFoundError
