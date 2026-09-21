"""SQL adapter for the GenerationRepository port (OPS-12).

Translates between the `core.generation_requests` / `core.generation_artifacts`
rows and the plain dataclasses in `core/generation/models.py`. This seam must
live here, not on the `core/` side, because it is the only layer allowed to
see both.
"""

from __future__ import annotations

from greader.core.generation.models import (
    AssignmentDraft,
    Citation,
    GenerationArtifact,
    ReviewStatus,
    TestCaseDraft,
)
from greader.database.core.tables import GenerationArtifact as GenerationArtifactRow
from greader.database.core.tables import GenerationRequest as GenerationRequestRow
from greader.database.session import SessionFactory


def _test_case_to_json(test_case: TestCaseDraft) -> dict[str, object]:
    return {
        "input_data": test_case.input_data,
        "expected_output": test_case.expected_output,
        "is_hidden": test_case.is_hidden,
        "order_index": test_case.order_index,
    }


def _test_case_from_json(data: dict[str, object]) -> TestCaseDraft:
    return TestCaseDraft(
        input_data=str(data["input_data"]),
        expected_output=str(data["expected_output"]),
        is_hidden=bool(data["is_hidden"]),
        order_index=int(data["order_index"]),
    )


def draft_to_json(draft: AssignmentDraft) -> dict[str, object]:
    """Serialize a draft to the JSON shape stored in `generation_artifacts.draft`.

    Public so `tests/fakes/generation.py` can round-trip through the same
    codec the SQL adapter uses, instead of storing the domain object as-is.
    """
    return {
        "title": draft.title,
        "statement": draft.statement,
        "test_cases": [_test_case_to_json(test_case) for test_case in draft.test_cases],
    }


def draft_from_json(data: dict[str, object]) -> AssignmentDraft:
    """Inverse of `draft_to_json`."""
    test_cases = data["test_cases"]
    return AssignmentDraft(
        title=str(data["title"]),
        statement=str(data["statement"]),
        test_cases=[_test_case_from_json(item) for item in test_cases],
    )


def citation_to_json(citation: Citation) -> dict[str, object]:
    """Serialize a citation to the `generation_artifacts.citations` JSON shape.

    Public so `tests/fakes/generation.py` can round-trip through it too.
    """
    return {
        "chunk_id": citation.chunk_id,
        "source_id": citation.source_id,
        "page": citation.page,
        "score": citation.score,
        "text_snapshot": citation.text_snapshot,
    }


def citation_from_json(data: dict[str, object]) -> Citation:
    """Inverse of `citation_to_json`."""
    page = data["page"]
    return Citation(
        chunk_id=int(data["chunk_id"]),
        source_id=int(data["source_id"]),
        page=int(page) if page is not None else None,
        score=float(data["score"]),
        text_snapshot=str(data["text_snapshot"]),
    )


def _to_domain(row: GenerationArtifactRow) -> GenerationArtifact:
    return GenerationArtifact(
        id=row.id,
        draft=draft_from_json(row.draft),
        citations=[citation_from_json(item) for item in row.citations],
        review_status=ReviewStatus(row.review_status),
    )


class SQLGenerationRepository:
    """Store generation requests and artifacts in the `core` schema.

    One session per method: the service is built once at startup, so there is
    no per-request session to join. Each call is its own unit of work.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def create_request(self, prompt: str, filters: dict[str, object]) -> int:
        """Insert a pending request row and return its generated id."""
        with self._session_factory() as session:
            row = GenerationRequestRow(prompt=prompt, filters=dict(filters))
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def mark_request_completed(self, request_id: int) -> None:
        """Mark a request as completed.

        Raises KeyError when the id does not exist: the service only ever
        calls this right after `create_request` returns that same id, so a
        missing row is a programming error, not something a caller recovers
        from.
        """
        with self._session_factory() as session:
            row = session.get(GenerationRequestRow, request_id)
            if row is None:
                raise KeyError(request_id)
            row.status = "completed"
            session.add(row)
            session.commit()

    def mark_request_failed(self, request_id: int, error_code: str) -> None:
        """Mark a request as failed, recording why."""
        with self._session_factory() as session:
            row = session.get(GenerationRequestRow, request_id)
            if row is None:
                raise KeyError(request_id)
            row.status = "failed"
            row.error_code = error_code
            session.add(row)
            session.commit()

    def create_artifact(
        self, request_id: int, draft: AssignmentDraft, citations: list[Citation]
    ) -> GenerationArtifact:
        """Insert an artifact linked to `request_id` and return it with an id."""
        with self._session_factory() as session:
            row = GenerationArtifactRow(
                request_id=request_id,
                draft=draft_to_json(draft),
                citations=[citation_to_json(citation) for citation in citations],
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def get(self, artifact_id: int) -> GenerationArtifact | None:
        """Return an artifact by id when present."""
        with self._session_factory() as session:
            row = session.get(GenerationArtifactRow, artifact_id)
            if row is None:
                return None
            return _to_domain(row)
