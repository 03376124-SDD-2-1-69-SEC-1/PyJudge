from typing import Protocol

from greader.core.test_cases.models import TestCase


class TestCaseRepository(Protocol):
    def create_test_case(self, test_case: TestCase) -> TestCase: ...

    def list_test_cases(self, assignment_id: int) -> list[TestCase]: ...

    def get_test_case(
        self, assignment_id: int, test_case_id: int
    ) -> TestCase | None: ...

    def update_test_case(
        self, assignment_id: int, test_case_id: int, test_case: TestCase
    ) -> TestCase | None: ...

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool: ...
