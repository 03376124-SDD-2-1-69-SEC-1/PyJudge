"""SQL adapter for the DraftRepository port (OPS-15).

Drafts get their own table and the daily Quota counts rows of
`core.generation_events`, one per successful generation or regeneration
(ADR-0008). A Draft's content, citations and settings are JSONB: the T-04
stepper reads and writes them whole and nothing queries them by field.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlmodel import select

from questly.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    JudgingSettings,
    Language,
)
from questly.core.generation.models import Draft, DraftSettings, DraftStatus
from questly.database.core.generation_repository import (
    citation_from_json,
    citation_to_json,
)
from questly.database.core.tables import DraftRow, GenerationEvent
from questly.database.core.version_repository import (
    decode_test_case,
    encode_test_case,
)
from questly.database.session import SessionFactory

ContentJson = dict[str, object]
SettingsJson = dict[str, str | int | bool | None]


def _content_to_json(content: AssignmentContent) -> ContentJson:
    return {
        "title": content.title,
        "problem_statement": content.problem_statement,
        "difficulty": content.difficulty.value,
        "test_cases": [encode_test_case(tc) for tc in content.test_cases],
        "topic_id": content.topic_id,
        "settings": {
            "time_limit_ms": content.settings.time_limit_ms,
            "language": content.settings.language.value,
            "show_hidden_names": content.settings.show_hidden_names,
        },
    }


def _content_from_json(data: ContentJson) -> AssignmentContent:
    judging = data["settings"]
    return AssignmentContent(
        title=data["title"],
        problem_statement=data["problem_statement"],
        difficulty=Difficulty(data["difficulty"]),
        test_cases=[decode_test_case(item) for item in data["test_cases"]],
        topic_id=data["topic_id"],
        settings=JudgingSettings(
            time_limit_ms=judging["time_limit_ms"],
            language=Language(judging["language"]),
            show_hidden_names=judging["show_hidden_names"],
        ),
    )


def _settings_to_json(settings: DraftSettings) -> SettingsJson:
    deadline = None
    if settings.deadline is not None:
        deadline = settings.deadline.isoformat()
    return {
        "deadline": deadline,
        "max_score": settings.max_score,
        "allow_late": settings.allow_late,
        "allow_resubmission": settings.allow_resubmission,
    }


def _settings_from_json(data: SettingsJson) -> DraftSettings:
    deadline = None
    if data["deadline"] is not None:
        deadline = datetime.fromisoformat(data["deadline"])
    return DraftSettings(
        deadline=deadline,
        max_score=data["max_score"],
        allow_late=data["allow_late"],
        allow_resubmission=data["allow_resubmission"],
    )


def _draft(row: DraftRow) -> Draft:
    return Draft(
        id=row.id,
        classroom_id=row.classroom_id,
        requested_by=row.requested_by,
        prompt=row.prompt,
        content=_content_from_json(row.content),
        generated_at=row.generated_at,
        citations=[citation_from_json(item) for item in row.citations],
        document_ids=list(row.document_ids),
        settings=_settings_from_json(row.settings),
        classroom_ids=list(row.classroom_ids),
        status=DraftStatus(row.status),
        assignment_id=row.assignment_id,
    )


def _write(row: DraftRow, draft: Draft) -> None:
    row.classroom_id = draft.classroom_id
    row.requested_by = draft.requested_by
    row.prompt = draft.prompt
    row.content = _content_to_json(draft.content)
    row.generated_at = draft.generated_at
    row.citations = [citation_to_json(citation) for citation in draft.citations]
    row.document_ids = list(draft.document_ids)
    row.settings = _settings_to_json(draft.settings)
    row.classroom_ids = list(draft.classroom_ids)
    row.status = draft.status.value
    row.assignment_id = draft.assignment_id


class SQLDraftRepository:
    """Store Drafts and the generation log behind the daily Quota."""

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def create(self, draft: Draft) -> Draft:
        """Insert a Draft and return it with its new id."""
        with self._session_factory() as db:
            row = DraftRow()
            _write(row, draft)
            db.add(row)
            db.commit()
            db.refresh(row)
            return _draft(row)

    def get(self, draft_id: int) -> Draft | None:
        """Return one Draft, if it exists."""
        with self._session_factory() as db:
            row = db.get(DraftRow, draft_id)
            if row is None:
                return None
            return _draft(row)

    def update(self, draft: Draft) -> Draft:
        """Replace an existing Draft; KeyError when the id is unknown."""
        with self._session_factory() as db:
            row = db.get(DraftRow, draft.id)
            if row is None:
                raise KeyError(draft.id)
            _write(row, draft)
            db.commit()
            db.refresh(row)
            return _draft(row)

    def delete(self, draft_id: int) -> bool:
        """Delete a Draft and report whether it existed."""
        with self._session_factory() as db:
            row = db.get(DraftRow, draft_id)
            if row is None:
                return False
            db.delete(row)
            db.commit()
            return True

    def list_for_classroom(self, classroom_id: int) -> list[Draft]:
        """Return Drafts generated in this Classroom, in id order.

        Matches the Draft's own Classroom, not its publishing targets.
        """
        with self._session_factory() as db:
            rows = db.exec(
                select(DraftRow)
                .where(DraftRow.classroom_id == classroom_id)
                .order_by(DraftRow.id)
            ).all()
            return [_draft(row) for row in rows]

    def record_generation(self, user_id: int, at: datetime) -> None:
        """Log one successful generation against the user's Quota."""
        with self._session_factory() as db:
            db.add(GenerationEvent(user_id=user_id, occurred_at=at))
            db.commit()

    def count_generations(self, user_id: int, since: datetime) -> int:
        """Count the user's generations at or after `since`."""
        with self._session_factory() as db:
            return db.exec(
                select(func.count())
                .select_from(GenerationEvent)
                .where(
                    GenerationEvent.user_id == user_id,
                    GenerationEvent.occurred_at >= since,
                )
            ).one()
