"""SQLAlchemy-backed assignment repository."""

from sqlalchemy.orm import Session, sessionmaker

from greader.assignments.mappers import (
    assignment_domain_to_record,
    assignment_record_to_domain,
)
from greader.assignments.models import Assignment
from greader.db_models import AssignmentRecord


class SqlAlchemyAssignmentRepository:
    """Repository implementation backed by a relational database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_assignments(self) -> list[Assignment]:
        """Return all assignments ordered by creation date."""
        with self._session_factory() as session:
            records = (
                session.query(AssignmentRecord)
                .order_by(AssignmentRecord.created_at)
                .all()
            )
            return [assignment_record_to_domain(r) for r in records]

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        """Return a single assignment by ID, or *None* if not found."""
        with self._session_factory() as session:
            record = session.get(AssignmentRecord, assignment_id)
            if record is None:
                return None
            return assignment_record_to_domain(record)

    def save_assignment(self, assignment: Assignment) -> None:
        """Create or update an assignment (upsert)."""
        with self._session_factory() as session:
            existing = session.get(AssignmentRecord, assignment.id)
            if existing is not None:
                # Update scalar fields.
                existing.title = assignment.title
                existing.description = assignment.description
                existing.input_format = assignment.input_format
                existing.output_format = assignment.output_format
                existing.constraints = assignment.constraints
                existing.difficulty = assignment.difficulty.value
                existing.programming_language = assignment.programming_language
                existing.status = assignment.status
                existing.reference_solution = assignment.reference_solution
                existing.coverage_score = assignment.coverage_score
                existing.mutation_score = assignment.mutation_score

                # Replace test cases (cascade handles orphan deletion).
                existing.test_cases.clear()
                record = assignment_domain_to_record(assignment)
                for tc in record.test_cases:
                    session.add(tc)
                    existing.test_cases.append(tc)
            else:
                record = assignment_domain_to_record(assignment)
                session.add(record)
            session.commit()

    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete an assignment and cascade-delete its test cases."""
        with self._session_factory() as session:
            record = session.get(AssignmentRecord, assignment_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True
