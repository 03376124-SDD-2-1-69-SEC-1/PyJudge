"""Assignment use cases independent from HTTP and database technology."""

from greader.core.assignments.models import Assignment
from greader.core.assignments.repository import AssignmentRepository


class AssignmentNotFoundError(Exception):
    """Raised when a requested Assignment does not exist."""


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
