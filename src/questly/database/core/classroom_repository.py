"""SQL adapter for the ClassroomRepository port (OPS-15)."""

from __future__ import annotations

from sqlalchemy import func
from sqlmodel import select

from questly.core.classrooms.models import Classroom, Membership
from questly.database.core.tables import Classroom as ClassroomRow
from questly.database.core.tables import ClassroomMember as MemberRow
from questly.database.session import SessionFactory


def _classroom(row: ClassroomRow) -> Classroom:
    return Classroom(
        id=row.id,
        instructor_id=row.instructor_id,
        course_code=row.course_code,
        course_name=row.course_name,
        section=row.section,
        semester=row.semester,
        join_code=row.join_code,
        archived=row.archived_at is not None,
    )


def _membership(row: MemberRow) -> Membership:
    return Membership(
        id=row.id,
        classroom_id=row.classroom_id,
        student_id=row.student_id,
        joined_at=row.joined_at,
    )


class SQLClassroomRepository:
    """Store Classrooms and their Members in the `core` schema.

    `archived` is `archived_at IS NOT NULL` (ADR-0008); archiving stamps the
    moment, un-archiving clears it.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def get(self, classroom_id: int) -> Classroom | None:
        """Return one Classroom, if it exists."""
        with self._session_factory() as db:
            row = db.get(ClassroomRow, classroom_id)
            if row is None:
                return None
            return _classroom(row)

    def list_owned_by(self, instructor_id: int) -> list[Classroom]:
        """Return an Instructor's Classrooms in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(ClassroomRow)
                .where(ClassroomRow.instructor_id == instructor_id)
                .order_by(ClassroomRow.id)
            ).all()
            return [_classroom(row) for row in rows]

    def list_joined_by(self, student_id: int) -> list[Classroom]:
        """Return the Classrooms a Student is a Member of, in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(ClassroomRow)
                .join(MemberRow, MemberRow.classroom_id == ClassroomRow.id)
                .where(MemberRow.student_id == student_id)
                .order_by(ClassroomRow.id)
            ).all()
            return [_classroom(row) for row in rows]

    def find_by_join_code(self, join_code: str) -> Classroom | None:
        """Return the Classroom holding exactly this Join code, if any."""
        with self._session_factory() as db:
            row = db.exec(
                select(ClassroomRow).where(ClassroomRow.join_code == join_code)
            ).first()
            if row is None:
                return None
            return _classroom(row)

    def create(self, classroom: Classroom) -> Classroom:
        """Insert a Classroom and return it with its new id."""
        with self._session_factory() as db:
            row = ClassroomRow(
                instructor_id=classroom.instructor_id,
                course_code=classroom.course_code,
                course_name=classroom.course_name,
                section=classroom.section,
                semester=classroom.semester,
                join_code=classroom.join_code,
                archived_at=func.now() if classroom.archived else None,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _classroom(row)

    def update(self, classroom: Classroom) -> Classroom:
        """Replace an existing Classroom; KeyError when the id is unknown."""
        with self._session_factory() as db:
            row = db.get(ClassroomRow, classroom.id)
            if row is None:
                raise KeyError(classroom.id)
            row.instructor_id = classroom.instructor_id
            row.course_code = classroom.course_code
            row.course_name = classroom.course_name
            row.section = classroom.section
            row.semester = classroom.semester
            row.join_code = classroom.join_code
            if not classroom.archived:
                row.archived_at = None
            elif row.archived_at is None:
                row.archived_at = func.now()
            db.commit()
            db.refresh(row)
            return _classroom(row)

    def get_membership(self, classroom_id: int, student_id: int) -> Membership | None:
        """Return one Student's Membership in one Classroom, if any."""
        with self._session_factory() as db:
            row = db.exec(
                select(MemberRow).where(
                    MemberRow.classroom_id == classroom_id,
                    MemberRow.student_id == student_id,
                )
            ).first()
            if row is None:
                return None
            return _membership(row)

    def list_memberships(self, classroom_id: int) -> list[Membership]:
        """Return a Classroom's Memberships in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(MemberRow)
                .where(MemberRow.classroom_id == classroom_id)
                .order_by(MemberRow.id)
            ).all()
            return [_membership(row) for row in rows]

    def add_membership(self, membership: Membership) -> Membership:
        """Insert a Membership; the pair is UNIQUE, the service checks first."""
        with self._session_factory() as db:
            row = MemberRow(
                classroom_id=membership.classroom_id,
                student_id=membership.student_id,
                joined_at=membership.joined_at,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _membership(row)

    def remove_membership(self, classroom_id: int, student_id: int) -> bool:
        """Delete one Membership and report whether it existed."""
        with self._session_factory() as db:
            row = db.exec(
                select(MemberRow).where(
                    MemberRow.classroom_id == classroom_id,
                    MemberRow.student_id == student_id,
                )
            ).first()
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True
