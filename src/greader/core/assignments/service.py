from typing import Any

from greader.core.assignments.models import Assignment, TestCase
from greader.core.assignments.repository import AssignmentRepository


class AssignmentService:
    def __init__(self, repo: AssignmentRepository) -> None:
        self._repo = repo

    def list_assignments_as_dict(self) -> list[dict[str, Any]]:
        assignments = self._repo.list_all()
        return [self._to_dict(a) for a in assignments]

    def get_assignment_as_dict(self, assignment_id: int) -> dict[str, Any] | None:
        assignment = self._repo.get_by_id(assignment_id)
        return self._to_dict(assignment) if assignment else None

    def create_assignment_as_dict(
        self,
        title: str,
        problem_statement: str,
        difficulty: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        assignment = Assignment(
            id=None,
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            metadata=metadata,
        )
        created = self._repo.create(assignment)
        return self._to_dict(created)

    def update_assignment_as_dict(
        self,
        assignment_id: int,
        title: str,
        problem_statement: str,
        difficulty: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        assignment = Assignment(
            id=assignment_id,
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            metadata=metadata,
        )
        updated = self._repo.update(assignment_id, assignment)
        return self._to_dict(updated) if updated else None

    def delete_assignment(self, assignment_id: int) -> bool:
        return self._repo.delete(assignment_id)

    # === Test Cases Operations ===
    def create_test_case_as_dict(
        self,
        assignment_id: int,
        input_data: str,
        expected_output: str,
        is_hidden: bool = False,
        weight: float = 1.0,
    ) -> dict[str, Any] | None:
        test_case = TestCase(
            input_data=input_data,
            expected_output=expected_output,
            is_hidden=is_hidden,
            weight=weight,
        )
        created = self._repo.create_test_case(assignment_id, test_case)
        return self._tc_to_dict(created) if created else None

    def list_test_cases_as_dict(
        self, assignment_id: int
    ) -> list[dict[str, Any]] | None:
        test_cases = self._repo.list_test_cases(assignment_id)
        if test_cases is None:
            return None
        return [self._tc_to_dict(tc) for tc in test_cases]

    def update_test_case_as_dict(
        self,
        assignment_id: int,
        test_case_id: int,
        input_data: str | None = None,
        expected_output: str | None = None,
        is_hidden: bool | None = None,
        weight: float | None = None,
    ) -> dict[str, Any] | None:
        test_case = TestCase(
            input_data=input_data or "",
            expected_output=expected_output or "",
            is_hidden=is_hidden if is_hidden is not None else False,
            weight=weight if weight is not None else 1.0,
        )
        updated = self._repo.update_test_case(assignment_id, test_case_id, test_case)
        return self._tc_to_dict(updated) if updated else None

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool:
        return self._repo.delete_test_case(assignment_id, test_case_id)

    def _tc_to_dict(self, tc: TestCase) -> dict[str, Any]:
        return {
            "id": tc.id,
            "assignment_id": tc.assignment_id,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "is_hidden": tc.is_hidden,
            "weight": tc.weight,
            "order_index": tc.order_index,
        }

    def _to_dict(self, assignment: Assignment) -> dict[str, Any]:
        test_cases = [self._tc_to_dict(tc) for tc in (assignment.test_cases or [])]
        return {
            "id": assignment.id,
            "title": assignment.title,
            "problem_statement": assignment.problem_statement,
            "difficulty": assignment.difficulty,
            "metadata": assignment.metadata,
            "artifact_id": assignment.artifact_id,
            "test_cases": test_cases,
        }
