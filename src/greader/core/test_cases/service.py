from typing import Any

from greader.core.test_cases.models import TestCase
from greader.core.test_cases.repository import TestCaseRepository


class TestCaseService:
    def __init__(self, repo: TestCaseRepository) -> None:
        self._repo = repo

    def create_test_case(
        self,
        assignment_id: int,
        input_data: str,
        expected_output: str,
        is_hidden: bool,
        order_index: int,
    ) -> dict[str, Any]:
        tc = TestCase(
            id=None,
            assignment_id=assignment_id,
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            order_index=order_index,
        )
        created = self._repo.create_test_case(tc)
        return self._to_dict(created)

    def list_test_cases(self, assignment_id: int) -> list[dict[str, Any]]:
        test_cases = self._repo.list_test_cases(assignment_id)
        return [self._to_dict(tc) for tc in test_cases]

    def get_test_case(
        self, assignment_id: int, test_case_id: int
    ) -> dict[str, Any] | None:
        tc = self._repo.get_test_case(assignment_id, test_case_id)
        return self._to_dict(tc) if tc else None

    def update_test_case(
        self,
        assignment_id: int,
        test_case_id: int,
        input_data: str | None = None,
        expected_output: str | None = None,
        is_hidden: bool | None = None,
        order_index: int | None = None,
    ) -> dict[str, Any] | None:
        existing = self._repo.get_test_case(assignment_id, test_case_id)
        if not existing:
            return None

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
        return self._to_dict(updated) if updated else None

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool:
        return self._repo.delete_test_case(assignment_id, test_case_id)

    def _to_dict(self, tc: TestCase) -> dict[str, Any]:
        return {
            "id": tc.id,
            "assignment_id": tc.assignment_id,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "is_hidden": tc.is_hidden,
            "order_index": tc.order_index,
        }
