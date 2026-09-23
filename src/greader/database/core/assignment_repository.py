"""SQL adapter for the AssignmentRepository port (CORE-10).

Translates between the `core.assignments` + `core.test_cases` rows and the plain
dataclasses in `core/assignments/models.py`. Test cases are reached only through
their Assignment, matching the aggregate CORE-11 settled on.
"""

from __future__ import annotations

from sqlalchemy.orm import selectinload
from sqlmodel import select

from greader.core.assignments.models import Assignment, TestCase, TestCaseKind
from greader.database.core.tables import Assignment as AssignmentRow
from greader.database.core.tables import TestCase as TestCaseRow
from greader.database.session import SessionFactory


def _to_domain(row: AssignmentRow) -> Assignment:
    """Map a row and its children to the domain aggregate.

    Children are ordered by `order_index` then id so two adapters reading the
    same data return the same list. `created_at`/`updated_at` stay on the row:
    the domain layer holds no field that exists only to satisfy a table.
    """
    children = sorted(row.test_cases, key=lambda child: (child.order_index, child.id))
    return Assignment(
        id=row.id,
        title=row.title,
        problem_statement=row.problem_statement,
        difficulty=row.difficulty,
        metadata=dict(row.metadata_),
        artifact_id=row.artifact_id,
        test_cases=[
            TestCase(
                id=child.id,
                input_data=child.input_data,
                expected_output=child.expected_output,
                # The table has only is_hidden until OPS-15 adds kind and note;
                # this adapter is not wired meanwhile (ADR-0007 §10.4).
                kind=TestCaseKind.HIDDEN if child.is_hidden else TestCaseKind.SAMPLE,
                order_index=child.order_index,
            )
            for child in children
        ],
    )


def _new_child_row(assignment_id: int, test_case: TestCase) -> TestCaseRow:
    return TestCaseRow(
        assignment_id=assignment_id,
        input_data=test_case.input_data,
        expected_output=test_case.expected_output,
        is_hidden=not test_case.visible_to_students,
        order_index=test_case.order_index,
    )


class SQLAssignmentRepository:
    """Store Assignments in the `core` schema.

    One session per method: the service is built once at startup and put on
    `app.state`, so there is no per-request session to join — each call is its
    own unit of work.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def list(self) -> list[Assignment]:
        """Return all stored Assignments, oldest first."""
        with self._session_factory() as session:
            rows = session.exec(
                select(AssignmentRow)
                .options(selectinload(AssignmentRow.test_cases))
                .order_by(AssignmentRow.id)
            ).all()
            return [_to_domain(row) for row in rows]

    def get(self, assignment_id: int) -> Assignment | None:
        """Return an Assignment by id when present."""
        with self._session_factory() as session:
            row = session.get(AssignmentRow, assignment_id)
            if row is None:
                return None
            return _to_domain(row)

    def create(self, assignment: Assignment) -> Assignment:
        """Insert an Assignment and return it with database-assigned ids.

        A test case arrives with `id` set to None and leaves with the id the
        sequence gave it, exactly as the parent does.
        """
        with self._session_factory() as session:
            row = AssignmentRow(
                title=assignment.title,
                problem_statement=assignment.problem_statement,
                difficulty=assignment.difficulty,
                metadata_=dict(assignment.metadata),
                artifact_id=assignment.artifact_id,
            )
            session.add(row)
            session.flush()
            for test_case in assignment.test_cases:
                session.add(_new_child_row(row.id, test_case))
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def update(self, assignment: Assignment) -> Assignment:
        """Replace a stored Assignment and reconcile its test cases.

        Raises KeyError when the id does not exist, matching the in-memory
        adapter: the Protocol says `update` takes an Assignment that already has
        its id, so a missing row is a programming error, not a 404.
        """
        with self._session_factory() as session:
            row = session.get(AssignmentRow, assignment.id)
            if row is None:
                raise KeyError(assignment.id)

            row.title = assignment.title
            row.problem_statement = assignment.problem_statement
            row.difficulty = assignment.difficulty
            row.metadata_ = dict(assignment.metadata)
            row.artifact_id = assignment.artifact_id

            stored_children = {child.id: child for child in row.test_cases}
            submitted_ids = {
                test_case.id
                for test_case in assignment.test_cases
                if test_case.id is not None
            }
            for child_id, child in stored_children.items():
                if child_id not in submitted_ids:
                    session.delete(child)

            for test_case in assignment.test_cases:
                if test_case.id is None:
                    session.add(_new_child_row(row.id, test_case))
                    continue
                child = stored_children[test_case.id]
                child.input_data = test_case.input_data
                child.expected_output = test_case.expected_output
                child.is_hidden = not test_case.visible_to_students
                child.order_index = test_case.order_index

            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def delete(self, assignment_id: int) -> bool:
        """Delete an Assignment and report whether it existed.

        Its test cases go with it through the ON DELETE CASCADE already on
        `core.test_cases.assignment_id`.
        """
        with self._session_factory() as session:
            row = session.get(AssignmentRow, assignment_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
