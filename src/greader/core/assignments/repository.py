from typing import Protocol

from greader.core.assignments.models import Assignment


class AssignmentRepository(Protocol):
    def list_all(self) -> list[Assignment]: ...

    def get_by_id(self, assignment_id: int) -> Assignment | None: ...

    def create(self, assignment: Assignment) -> Assignment: ...

    def update(
        self, assignment_id: int, assignment: Assignment
    ) -> Assignment | None: ...

    def delete(self, assignment_id: int) -> bool: ...


class InMemoryAssignmentRepository:
    def __init__(self) -> None:
        self._items: dict[int, Assignment] = {}
        self._next_id: int = 1

    def list_all(self) -> list[Assignment]:
        return list(self._items.values())

    def get_by_id(self, assignment_id: int) -> Assignment | None:
        return self._items.get(assignment_id)

    def create(self, assignment: Assignment) -> Assignment:
        new_id = self._next_id
        self._next_id += 1
        created = Assignment(
            id=new_id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=assignment.test_cases or [],
        )
        self._items[new_id] = created
        return created

    def update(self, assignment_id: int, assignment: Assignment) -> Assignment | None:
        if assignment_id not in self._items:
            return None
        updated = Assignment(
            id=assignment_id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=self._items[assignment_id].created_at,
            updated_at=assignment.updated_at,
            test_cases=assignment.test_cases or [],
        )
        self._items[assignment_id] = updated
        return updated

    def delete(self, assignment_id: int) -> bool:
        if assignment_id not in self._items:
            return False
        del self._items[assignment_id]
        return True
