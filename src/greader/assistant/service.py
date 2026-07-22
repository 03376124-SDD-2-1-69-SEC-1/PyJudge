"""Application service for assignment generation."""

from __future__ import annotations

from pydantic import ValidationError

from greader.assignments.models import Assignment
from greader.assignments.repository import AssignmentRepository
from greader.assistant.errors import GenerationError
from greader.assistant.interface import AssignmentGenerator, GenerationRequest
from greader.assistant.models import GenerationArtifact
from greader.assistant.repository import SqlAlchemyGenerationRepository
from greader.assistant.schemas import (
    FullAssignmentDraft,
    GenerationMode,
    TestCaseDraftSet,
)


class AssignmentGenerationService:
    """Coordinates validation, provider calls, and generation persistence."""

    def __init__(
        self,
        *,
        assignment_repository: AssignmentRepository,
        generation_repository: SqlAlchemyGenerationRepository,
        generator: AssignmentGenerator,
    ) -> None:
        self._assignment_repository = assignment_repository
        self._generation_repository = generation_repository
        self._generator = generator

    def generate(
        self,
        *,
        prompt: str,
        mode: GenerationMode,
        assignment_id: str | None,
    ) -> GenerationArtifact:
        """Generate, validate, persist, and return an artifact."""
        try:
            request = GenerationRequest(
                prompt=prompt,
                mode=mode,
                assignment_id=assignment_id,
            )
        except ValidationError as exc:
            raise GenerationError("invalid_prompt") from exc

        assignment = self._load_assignment(request)
        request_id = self._generation_repository.create_request(
            prompt=request.prompt,
            mode=request.mode,
            assignment_id=assignment.id if assignment else None,
            provider=getattr(self._generator, "provider_name", "unknown"),
            model_name=getattr(self._generator, "model_name", "unknown"),
        )

        try:
            result = self._generator.generate(request, assignment)
            if result.mode is not request.mode:
                raise GenerationError("provider_invalid_response")
            payload = _validate_payload(result.mode, result.payload)
        except GenerationError as exc:
            self._generation_repository.mark_failed(request_id, exc.safe_error_code)
            raise
        except Exception as exc:
            self._generation_repository.mark_failed(request_id, "provider_unavailable")
            raise GenerationError("provider_unavailable") from exc

        self._generation_repository.mark_succeeded(request_id)
        return self._generation_repository.save_artifact(
            request_id=request_id,
            mode=result.mode,
            provider=result.provider,
            model_name=result.model_name,
            summary=result.summary,
            payload=payload,
        )

    def _load_assignment(self, request: GenerationRequest) -> Assignment | None:
        if request.mode is GenerationMode.FULL_ASSIGNMENT:
            return None
        if request.assignment_id is None:
            raise GenerationError("assignment_required")
        assignment = self._assignment_repository.get_assignment(request.assignment_id)
        if assignment is None:
            raise GenerationError("assignment_required")
        return assignment


def _validate_payload(
    mode: GenerationMode,
    payload: FullAssignmentDraft | TestCaseDraftSet,
) -> FullAssignmentDraft | TestCaseDraftSet:
    try:
        if mode is GenerationMode.FULL_ASSIGNMENT:
            return FullAssignmentDraft.model_validate(payload)
        return TestCaseDraftSet.model_validate(payload)
    except ValidationError as exc:
        raise GenerationError("provider_invalid_response") from exc
