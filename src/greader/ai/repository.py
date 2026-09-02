"""SQLAlchemy repository for generation requests and artifacts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from greader.ai.errors import ArtifactReviewError
from greader.ai.models import ArtifactStatus, GenerationArtifact
from greader.ai.schemas import DraftPayload, FullAssignmentDraft, GenerationMode
from greader.assignments.mappers import (
    assignment_domain_to_record,
    test_case_domain_to_record,
)
from greader.assignments.models import Assignment, TestCase
from greader.db_models import (
    AssignmentRecord,
    GenerationArtifactRecord,
    GenerationRequestRecord,
    TestCaseRecord,
)


def normalize_test_value(value: str) -> str:
    """Normalize test data for duplicate comparison without changing inner spaces."""
    lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized = [line.rstrip() for line in lines]
    while normalized and normalized[-1] == "":
        normalized.pop()
    return "\n".join(normalized)


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
                review_status=ArtifactStatus.DRAFT.value,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            request = record.generation_request
            return GenerationArtifact(
                id=record.id,
                generation_request_id=record.generation_request_id,
                mode=GenerationMode(record.generation_mode),
                provider=provider,
                model_name=model_name,
                summary=summary,
                payload=payload,
                assignment_id=request.assignment_id,
                review_status=ArtifactStatus(record.review_status),
                created_at=record.created_at,
                reviewed_at=record.reviewed_at,
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
                from greader.ai.schemas import TestCaseDraftSet

                payload = TestCaseDraftSet.model_validate_json(record.payload_json)
            return GenerationArtifact(
                id=record.id,
                generation_request_id=record.generation_request_id,
                mode=mode,
                provider=request.provider,
                model_name=request.model_name,
                summary="Persisted generation artifact.",
                payload=payload,
                assignment_id=request.assignment_id,
                review_status=ArtifactStatus(record.review_status),
                created_at=record.created_at,
                reviewed_at=record.reviewed_at,
            )

    def apply_full_assignment(
        self,
        artifact_id: str,
        assignment: Assignment,
    ) -> None:
        """Create an assignment and mark its artifact applied in one transaction."""
        with self._session_factory() as session:
            artifact = self._get_draft_record(session, artifact_id)
            session.add(assignment_domain_to_record(assignment))
            artifact.review_status = ArtifactStatus.APPLIED.value
            artifact.reviewed_at = datetime.now(UTC)
            session.commit()

    def apply_test_cases(
        self,
        artifact_id: str,
        assignment_id: str,
        test_cases: list[TestCase],
    ) -> tuple[int, int]:
        """Insert non-duplicate cases and apply the artifact atomically."""
        with self._session_factory() as session:
            artifact = self._get_draft_record(session, artifact_id)
            assignment = session.get(AssignmentRecord, assignment_id)
            if assignment is None:
                raise ArtifactReviewError("assignment_not_found")

            existing = {
                (
                    normalize_test_value(record.input_data),
                    normalize_test_value(record.expected_output),
                )
                for record in session.query(TestCaseRecord)
                .filter(TestCaseRecord.assignment_id == assignment_id)
                .all()
            }
            saved_count = 0
            duplicate_count = 0
            for test_case in test_cases:
                key = (
                    normalize_test_value(test_case.input_data),
                    normalize_test_value(test_case.expected_output),
                )
                if key in existing:
                    duplicate_count += 1
                    continue
                existing.add(key)
                session.add(test_case_domain_to_record(test_case, assignment_id))
                saved_count += 1

            artifact.review_status = ArtifactStatus.APPLIED.value
            artifact.reviewed_at = datetime.now(UTC)
            session.commit()
            return saved_count, duplicate_count

    def discard_artifact(self, artifact_id: str) -> None:
        """Mark a draft artifact discarded while retaining its audit record."""
        with self._session_factory() as session:
            artifact = self._get_draft_record(session, artifact_id)
            artifact.review_status = ArtifactStatus.DISCARDED.value
            artifact.reviewed_at = datetime.now(UTC)
            session.commit()

    @staticmethod
    def _get_draft_record(
        session: Session,
        artifact_id: str,
    ) -> GenerationArtifactRecord:
        artifact = session.get(GenerationArtifactRecord, artifact_id)
        if artifact is None:
            raise ArtifactReviewError("artifact_not_found")
        if artifact.review_status == ArtifactStatus.APPLIED.value:
            raise ArtifactReviewError("artifact_already_applied")
        if artifact.review_status == ArtifactStatus.DISCARDED.value:
            raise ArtifactReviewError("artifact_discarded")
        return artifact
