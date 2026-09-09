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
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assignment = Assignment(
            id=None,
            title=title,
            problem_statement=problem_statement,
            difficulty=difficulty,
            metadata=metadata if metadata is not None else {},
        )
        created = self._repo.create(assignment)
        return self._to_dict(created)

    def update_assignment_as_dict(
        self,
        assignment_id: int,
        title: str | None = None,
        problem_statement: str | None = None,
        difficulty: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        existing = self._repo.get_by_id(assignment_id)
        if not existing:
            return None

        # Partial update logic: ถ้า field ไหนไม่ได้ส่งมา ให้ใช้ค่าเดิมของ assignment
        updated_assignment = Assignment(
            id=assignment_id,
            title=title if title is not None else existing.title,
            problem_statement=problem_statement
            if problem_statement is not None
            else existing.problem_statement,
            difficulty=difficulty if difficulty is not None else existing.difficulty,
            metadata=metadata if metadata is not None else existing.metadata or {},
            artifact_id=existing.artifact_id,
        )
        updated = self._repo.update(assignment_id, updated_assignment)
        return self._to_dict(updated) if updated else None

    def delete_assignment(self, assignment_id: int) -> bool:
        return self._repo.delete(assignment_id)

    def _to_dict(self, assignment: Assignment) -> dict[str, Any]:
        return {
            "id": assignment.id,
            "title": assignment.title,
            "problem_statement": assignment.problem_statement,
            "difficulty": assignment.difficulty,
            "metadata": assignment.metadata if assignment.metadata is not None else {},
            "artifact_id": assignment.artifact_id,
        }
