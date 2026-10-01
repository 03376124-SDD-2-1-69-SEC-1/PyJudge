"""SQL adapter for the PostingRepository port (OPS-15)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from questly.core.assignments.models import Posting, Schedule
from questly.database.core.tables import Posting as PostingRow
from questly.database.session import SessionFactory


def _posting(row: PostingRow) -> Posting:
    return Posting(
        id=row.id,
        classroom_id=row.classroom_id,
        assignment_id=row.assignment_id,
        schedule=Schedule(
            deadline=row.deadline,
            max_score=row.max_score,
            allow_late=row.allow_late,
            allow_resubmission=row.allow_resubmission,
        ),
        published_at=row.published_at,
        closed_at=row.closed_at,
    )


def _write(row: PostingRow, posting: Posting) -> None:
    row.classroom_id = posting.classroom_id
    row.assignment_id = posting.assignment_id
    row.deadline = posting.schedule.deadline
    row.max_score = posting.schedule.max_score
    row.allow_late = posting.schedule.allow_late
    row.allow_resubmission = posting.schedule.allow_resubmission
    row.published_at = posting.published_at
    row.closed_at = posting.closed_at


class SQLPostingRepository:
    """Store Postings in `core.classroom_assignments`."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def create(self, posting: Posting) -> Posting:
        """Insert a Posting; posting twice to one Classroom raises ValueError."""
        with self._session_factory() as db:
            row = PostingRow(
                classroom_id=posting.classroom_id,
                assignment_id=posting.assignment_id,
                deadline=posting.schedule.deadline,
                max_score=posting.schedule.max_score,
                allow_late=posting.schedule.allow_late,
                allow_resubmission=posting.schedule.allow_resubmission,
                published_at=posting.published_at,
                closed_at=posting.closed_at,
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError as error:
                db.rollback()
                raise ValueError(
                    "an assignment is posted once per classroom"
                ) from error
            db.refresh(row)
            return _posting(row)

    def update(self, posting: Posting) -> Posting:
        """Replace an existing Posting; KeyError when the id is unknown."""
        with self._session_factory() as db:
            row = db.get(PostingRow, posting.id)
            if row is None:
                raise KeyError(posting.id)
            _write(row, posting)
            db.commit()
            db.refresh(row)
            return _posting(row)

    def delete(self, posting_id: int) -> bool:
        """Delete a Posting and, by cascade, its Submissions (ADR-0008)."""
        with self._session_factory() as db:
            row = db.get(PostingRow, posting_id)
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True

    def find(self, classroom_id: int, assignment_id: int) -> Posting | None:
        """Return the Posting of one Assignment in one Classroom, if any."""
        with self._session_factory() as db:
            row = db.exec(
                select(PostingRow).where(
                    PostingRow.classroom_id == classroom_id,
                    PostingRow.assignment_id == assignment_id,
                )
            ).first()
            if row is None:
                return None
            return _posting(row)

    def list_for_classroom(self, classroom_id: int) -> list[Posting]:
        """Return a Classroom's Postings in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(PostingRow)
                .where(PostingRow.classroom_id == classroom_id)
                .order_by(PostingRow.id)
            ).all()
            return [_posting(row) for row in rows]

    def list_for_assignment(self, assignment_id: int) -> list[Posting]:
        """Return an Assignment's Postings in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(PostingRow)
                .where(PostingRow.assignment_id == assignment_id)
                .order_by(PostingRow.id)
            ).all()
            return [_posting(row) for row in rows]
