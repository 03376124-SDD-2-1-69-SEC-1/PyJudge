"""SQLAlchemy repository for generation requests and artifacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from greader.assistant.models import GenerationArtifact
from greader.assistant.schemas import DraftPayload, FullAssignmentDraft, GenerationMode
from greader.db_models import (
    AssignmentRecord,
    GenerationArtifactRecord,
    GenerationRequestRecord,
)


class SqlAlchemyGenerationRepository:
    """Persistence operations for AI generation audit records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_request(
        self,
        *,
        prompt: str,
        mode: GenerationMode,
        assignment_id: str | None,
        provider: str,
        model_name: str,
    ) -> str:
        """Create a pending request and return its ID."""
        request_id = str(uuid.uuid4())
        with self._session_factory() as session:
            stored_assignment_id = assignment_id
            if (
                stored_assignment_id is not None
                and session.get(AssignmentRecord, stored_assignment_id) is None
            ):
                stored_assignment_id = None
            session.add(
                GenerationRequestRecord(
                    id=request_id,
                    prompt=prompt,
                    generation_mode=mode.value,
                    assignment_id=stored_assignment_id,
                    provider=provider,
                    model_name=model_name,
                    status="pending",
                )
            )
            session.commit()
        return request_id

    def mark_succeeded(self, request_id: str) -> None:
        """Mark a generation request as succeeded."""
        with self._session_factory() as session:
            record = session.get(GenerationRequestRecord, request_id)
            if record is None:
                raise KeyError(request_id)
            record.status = "succeeded"
            record.safe_error_code = None
            record.completed_at = datetime.now(UTC)
            session.commit()

    def mark_failed(self, request_id: str, safe_error_code: str) -> None:
        """Mark a generation request as failed with a safe error code."""
        with self._session_factory() as session:
            record = session.get(GenerationRequestRecord, request_id)
            if record is None:
                raise KeyError(request_id)
            record.status = "failed"
            record.safe_error_code = safe_error_code
            record.completed_at = datetime.now(UTC)
            session.commit()

    def save_artifact(
        self,
        *,
        request_id: str,
        mode: GenerationMode,
        provider: str,
        model_name: str,
        summary: str,
        payload: DraftPayload,
    ) -> GenerationArtifact:
        """Persist a validated generation artifact."""
        artifact_id = str(uuid.uuid4())
        payload_json = payload.model_dump_json()
        with self._session_factory() as session:
            record = GenerationArtifactRecord(
                id=artifact_id,
                generation_request_id=request_id,
                generation_mode=mode.value,
                payload_json=payload_json,
                is_applied=False,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return GenerationArtifact(
                id=record.id,
                generation_request_id=record.generation_request_id,
                mode=GenerationMode(record.generation_mode),
                provider=provider,
                model_name=model_name,
                summary=summary,
                payload=payload,
                is_applied=record.is_applied,
                created_at=record.created_at,
                applied_at=record.applied_at,
            )

    def get_artifact(self, artifact_id: str) -> GenerationArtifact | None:
        """Return a persisted artifact, or None when missing."""
        with self._session_factory() as session:
            record = session.get(GenerationArtifactRecord, artifact_id)
            if record is None:
                return None
            request = record.generation_request
            mode = GenerationMode(record.generation_mode)
            payload: DraftPayload
            if mode is GenerationMode.FULL_ASSIGNMENT:
                payload = FullAssignmentDraft.model_validate_json(record.payload_json)
            else:
                from greader.assistant.schemas import TestCaseDraftSet

                payload = TestCaseDraftSet.model_validate_json(record.payload_json)
            return GenerationArtifact(
                id=record.id,
                generation_request_id=record.generation_request_id,
                mode=mode,
                provider=request.provider,
                model_name=request.model_name,
                summary="Persisted generation artifact.",
                payload=payload,
                is_applied=record.is_applied,
                created_at=record.created_at,
                applied_at=record.applied_at,
            )
