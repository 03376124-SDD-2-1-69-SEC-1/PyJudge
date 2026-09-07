from sqlmodel import Session, select

from greader.core.assignments.models import Assignment as DomainAssignment
from greader.core.assignments.models import TestCase as DomainTestCase
from greader.database.core.tables import Assignment as DBAssignment


class SQLAssignmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DomainAssignment]:
        statement = select(DBAssignment)
        results = self.session.exec(statement).all()
        return [self._to_domain(item) for item in results]

    def get_by_id(self, assignment_id: int) -> DomainAssignment | None:
        db_item = self.session.get(DBAssignment, assignment_id)
        return self._to_domain(db_item) if db_item else None

    def create(self, assignment: DomainAssignment) -> DomainAssignment:
        db_item = DBAssignment(
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata_=assignment.metadata,
        )
        self.session.add(db_item)
        self.session.commit()
        self.session.refresh(db_item)
        return self._to_domain(db_item)

    def update(
        self, assignment_id: int, assignment: DomainAssignment
    ) -> DomainAssignment | None:
        db_item = self.session.get(DBAssignment, assignment_id)
        if not db_item:
            return None
        db_item.title = assignment.title
        db_item.problem_statement = assignment.problem_statement
        db_item.difficulty = assignment.difficulty
        db_item.metadata_ = assignment.metadata
        self.session.add(db_item)
        self.session.commit()
        self.session.refresh(db_item)
        return self._to_domain(db_item)

    def delete(self, assignment_id: int) -> bool:
        db_item = self.session.get(DBAssignment, assignment_id)
        if not db_item:
            return False
        self.session.delete(db_item)
        self.session.commit()
        return True

    def _to_domain(self, db_item: DBAssignment) -> DomainAssignment:
        test_cases = [
            DomainTestCase(
                id=tc.id,
                assignment_id=tc.assignment_id,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                is_hidden=tc.is_hidden,
                order_index=tc.order_index,
                created_at=tc.created_at,
                updated_at=tc.updated_at,
            )
            for tc in getattr(db_item, "test_cases", [])
        ]
        return DomainAssignment(
            id=db_item.id,
            artifact_id=db_item.artifact_id,
            title=db_item.title,
            problem_statement=db_item.problem_statement,
            difficulty=db_item.difficulty,
            metadata=db_item.metadata_,
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            test_cases=test_cases,
        )
