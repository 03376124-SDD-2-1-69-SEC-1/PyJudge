"""SQL adapter for the VersionRepository port (OPS-15)."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from questly.core.assignments.models import (
    AssignmentVersion,
    Difficulty,
    JudgingSettings,
    Language,
    TestCase,
    TestCaseKind,
)
from questly.database.core.tables import AssignmentVersionRow as VersionRow
from questly.database.session import SessionFactory

TestCaseJson = dict[str, str | int | None]


def test_case_to_json(test_case: TestCase) -> TestCaseJson:
    """Serialize a Test Case; Draft content reuses this shape."""
    return {
        "id": test_case.id,
        "input_data": test_case.input_data,
        "expected_output": test_case.expected_output,
        "kind": test_case.kind.value,
        "note": test_case.note,
        "order_index": test_case.order_index,
    }


def test_case_from_json(data: TestCaseJson) -> TestCase:
    return TestCase(
        id=data["id"],
        input_data=data["input_data"],
        expected_output=data["expected_output"],
        kind=TestCaseKind(data["kind"]),
        note=data["note"],
        order_index=data["order_index"],
    )


def _version(row: VersionRow) -> AssignmentVersion:
    return AssignmentVersion(
        id=row.id,
        assignment_id=row.assignment_id,
        number=row.number,
        title=row.title,
        problem_statement=row.problem_statement,
        difficulty=Difficulty(row.difficulty),
        settings=JudgingSettings(
            time_limit_ms=row.time_limit_ms,
            language=Language(row.language),
            show_hidden_names=row.show_hidden_names,
        ),
        reason=row.reason,
        changed_at=row.created_at,
        test_cases=[test_case_from_json(item) for item in row.test_cases],
    )


class SQLVersionRepository:
    """Store immutable Assignment Versions; Test Cases are a JSONB snapshot."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def append(self, version: AssignmentVersion) -> AssignmentVersion:
        """Insert a Version; a number already used raises ValueError."""
        with self._session_factory() as db:
            row = VersionRow(
                assignment_id=version.assignment_id,
                number=version.number,
                title=version.title,
                problem_statement=version.problem_statement,
                difficulty=version.difficulty.value,
                test_cases=[test_case_to_json(tc) for tc in version.test_cases],
                time_limit_ms=version.settings.time_limit_ms,
                language=version.settings.language.value,
                show_hidden_names=version.settings.show_hidden_names,
                reason=version.reason,
                created_at=version.changed_at,
            )
            db.add(row)
            try:
                db.commit()
            except IntegrityError as error:
                db.rollback()
                raise ValueError("version numbers are unique per assignment") from error
            db.refresh(row)
            return _version(row)

    def list_for(self, assignment_id: int) -> list[AssignmentVersion]:
        """Return an Assignment's Versions in the order they were appended."""
        with self._session_factory() as db:
            rows = db.exec(
                select(VersionRow)
                .where(VersionRow.assignment_id == assignment_id)
                .order_by(VersionRow.id)
            ).all()
            return [_version(row) for row in rows]

    def get(self, assignment_id: int, number: int) -> AssignmentVersion | None:
        """Return one Version, if it exists."""
        with self._session_factory() as db:
            row = db.exec(
                select(VersionRow).where(
                    VersionRow.assignment_id == assignment_id,
                    VersionRow.number == number,
                )
            ).first()
            if row is None:
                return None
            return _version(row)
