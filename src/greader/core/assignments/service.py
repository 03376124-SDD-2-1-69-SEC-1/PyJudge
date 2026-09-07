from typing import Any

from greader.core.assignments.models import Assignment
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

    def _to_dict(self, assignment: Assignment) -> dict[str, Any]:
        test_cases = [
            {
                "id": tc.id,
                "assignment_id": tc.assignment_id,
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "is_hidden": tc.is_hidden,
                "order_index": tc.order_index,
            }
            for tc in (assignment.test_cases or [])
        ]
        return {
            "id": assignment.id,
            "title": assignment.title,
            "problem_statement": assignment.problem_statement,
            "difficulty": assignment.difficulty,
            "metadata": assignment.metadata,
            "artifact_id": assignment.artifact_id,
            "test_cases": test_cases,
        }
