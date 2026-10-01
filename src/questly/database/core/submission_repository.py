"""SQL adapter for the SubmissionRepository port (OPS-15)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select

from questly.core.assignments.models import TestCaseKind
from questly.core.submissions.models import Submission, TestResult, Verdict
from questly.database.core.tables import Posting as PostingRow
from questly.database.core.tables import SubmissionRow
from questly.database.core.tables import SubmissionTestResult as ResultRow
from questly.database.session import SessionFactory


def _result(row: ResultRow) -> TestResult:
    return TestResult(
        position=row.position,
        ordinal=row.ordinal,
        kind=TestCaseKind(row.kind),
        note=row.note,
        verdict=Verdict(row.verdict),
        time_seconds=row.time_seconds,
        expected_output=row.expected_output,
        actual_output=row.actual_output,
        error=row.error,
    )


def _submission(
    row: SubmissionRow, posting: PostingRow, results: list[ResultRow]
) -> Submission:
    return Submission(
        id=row.id,
        posting_id=row.posting_id,
        classroom_id=posting.classroom_id,
        assignment_id=posting.assignment_id,
        student_id=row.student_id,
        version_number=row.version_number,
        code=row.code,
        language=row.language,
        submitted_at=row.submitted_at,
        is_late=row.is_late,
        score=row.score,
        max_score=row.max_score,
        attempt=row.attempt,
        results=tuple(_result(result) for result in results),
    )


class SQLSubmissionRepository:
    """Store Submissions and one result row per Test Case.

    A Submission's Classroom and Assignment are read from its Posting, not
    stored twice (ADR-0008); its max score is stored, because the Posting's
    can change after grading.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def add(self, submission: Submission) -> Submission:
        """Insert a judged Submission with its results, in one transaction."""
        with self._session_factory() as db:
            row = SubmissionRow(
                posting_id=submission.posting_id,
                student_id=submission.student_id,
                version_number=submission.version_number,
                code=submission.code,
                language=submission.language,
                submitted_at=submission.submitted_at,
                is_late=submission.is_late,
                score=submission.score,
                max_score=submission.max_score,
                attempt=submission.attempt,
            )
            db.add(row)
            db.flush()
            for result in submission.results:
                db.add(
                    ResultRow(
                        submission_id=row.id,
                        position=result.position,
                        ordinal=result.ordinal,
                        kind=result.kind.value,
                        note=result.note,
                        verdict=result.verdict.value,
                        time_seconds=result.time_seconds,
                        expected_output=result.expected_output,
                        actual_output=result.actual_output,
                        error=result.error,
                    )
                )
            db.commit()
            return self._load(db, SubmissionRow.id == row.id)[0]

    def get(self, submission_id: int) -> Submission | None:
        """Return one Submission with its results, if it exists."""
        with self._session_factory() as db:
            found = self._load(db, SubmissionRow.id == submission_id)
            if not found:
                return None
            return found[0]

    def list_for_student(
        self, posting_id: int, student_id: int
    ) -> tuple[Submission, ...]:
        """One Student's Submissions on a Posting, oldest first."""
        with self._session_factory() as db:
            return tuple(
                self._load(
                    db,
                    SubmissionRow.posting_id == posting_id,
                    SubmissionRow.student_id == student_id,
                )
            )

    def list_for_posting(self, posting_id: int) -> tuple[Submission, ...]:
        """Every Student's Submissions on a Posting, oldest first."""
        with self._session_factory() as db:
            return tuple(self._load(db, SubmissionRow.posting_id == posting_id))

    def _load(self, db: Session, *conditions: ColumnElement[bool]) -> list[Submission]:
        """Read matching Submissions oldest first, with Posting and results."""
        pairs: Sequence[tuple[SubmissionRow, PostingRow]] = db.exec(
            select(SubmissionRow, PostingRow)
            .join(PostingRow, PostingRow.id == SubmissionRow.posting_id)
            .where(*conditions)
            .order_by(SubmissionRow.submitted_at, SubmissionRow.id)
        ).all()
        if not pairs:
            return []
        ids = [row.id for row, _ in pairs]
        results: dict[int, list[ResultRow]] = defaultdict(list)
        for result in db.exec(
            select(ResultRow)
            .where(ResultRow.submission_id.in_(ids))
            .order_by(ResultRow.submission_id, ResultRow.position)
        ).all():
            results[result.submission_id].append(result)
        return [_submission(row, posting, results[row.id]) for row, posting in pairs]
