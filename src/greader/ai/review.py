"""Application service for reviewing generated AI artifacts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from greader.ai.errors import ArtifactReviewError
from greader.ai.models import ArtifactStatus
from greader.ai.repository import SqlAlchemyGenerationRepository
from greader.ai.schemas import FullAssignmentDraft, GenerationMode, TestCaseDraftSet
from greader.assignments.models import Assignment, ReviewStatus, TestCase


@dataclass(frozen=True)
class ArtifactApplyResult:
    """Summary of content persisted from one reviewed artifact."""

    assignment_id: str
    selected_count: int
    saved_count: int
    duplicate_count: int = 0


class ArtifactReviewService:
    """Apply or discard a persisted generation artifact."""

    def __init__(
        self,
        *,
        generation_repository: SqlAlchemyGenerationRepository,
    ) -> None:
        self._generation_repository = generation_repository

    def apply_artifact(
        self,
        artifact_id: str,
        selected_indexes: list[int],
    ) -> ArtifactApplyResult:
        """Apply a draft according to its generation mode."""
        artifact = self._generation_repository.get_artifact(artifact_id)
        if artifact is None:
            raise ArtifactReviewError("artifact_not_found")
        if artifact.review_status is ArtifactStatus.APPLIED:
            raise ArtifactReviewError("artifact_already_applied")
        if artifact.review_status is ArtifactStatus.DISCARDED:
            raise ArtifactReviewError("artifact_discarded")

        if artifact.mode is GenerationMode.FULL_ASSIGNMENT:
            if not isinstance(artifact.payload, FullAssignmentDraft):
                raise ArtifactReviewError("artifact_invalid")
            return self._apply_full_assignment(artifact_id, artifact.payload)

        if not isinstance(artifact.payload, TestCaseDraftSet):
            raise ArtifactReviewError("artifact_invalid")
        if artifact.assignment_id is None:
            raise ArtifactReviewError("assignment_not_found")
        return self._apply_test_cases(
            artifact_id,
            artifact.assignment_id,
            artifact.payload,
            selected_indexes,
        )

    def discard_artifact(self, artifact_id: str) -> None:
        """Discard a draft artifact without deleting its audit trail."""
        self._generation_repository.discard_artifact(artifact_id)

    def _apply_full_assignment(
        self,
        artifact_id: str,
        draft: FullAssignmentDraft,
    ) -> ArtifactApplyResult:
        assignment_id = str(uuid.uuid4())
        test_cases = [
            TestCase(
                id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                input_data=generated.input_data,
                expected_output=generated.expected_output,
                category=generated.category,
                status=ReviewStatus.PENDING,
                explanation=generated.explanation,
            )
            for generated in draft.test_cases
        ]
        assignment = Assignment(
            id=assignment_id,
            title=draft.title,
            description=draft.problem_statement,
            input_format=draft.input_format,
            output_format=draft.output_format,
            constraints="\n".join(draft.constraints),
            difficulty=draft.difficulty,
            programming_language="Python",
            status="Draft",
            reference_solution=draft.reference_solution,
            test_cases=test_cases,
            ai_suggestions=[*draft.learning_objectives, *draft.ambiguity_notes],
        )
        self._generation_repository.apply_full_assignment(artifact_id, assignment)
        return ArtifactApplyResult(
            assignment_id=assignment_id,
            selected_count=len(test_cases),
            saved_count=len(test_cases),
        )

    def _apply_test_cases(
        self,
        artifact_id: str,
        assignment_id: str,
        draft: TestCaseDraftSet,
        selected_indexes: list[int],
    ) -> ArtifactApplyResult:
        unique_indexes = list(dict.fromkeys(selected_indexes))
        if not unique_indexes:
            raise ArtifactReviewError("no_test_cases_selected")
        if any(index < 0 or index >= len(draft.test_cases) for index in unique_indexes):
            raise ArtifactReviewError("invalid_test_case_selection")

        selected = [draft.test_cases[index] for index in unique_indexes]
        test_cases = [
            TestCase(
                id=str(uuid.uuid4()),
                assignment_id=assignment_id,
                input_data=generated.input_data,
                expected_output=generated.expected_output,
                category=generated.category,
                status=ReviewStatus.PENDING,
                explanation=generated.explanation,
            )
            for generated in selected
        ]
        saved_count, duplicate_count = self._generation_repository.apply_test_cases(
            artifact_id,
            assignment_id,
            test_cases,
        )
        return ArtifactApplyResult(
            assignment_id=assignment_id,
            selected_count=len(selected),
            saved_count=saved_count,
            duplicate_count=duplicate_count,
        )
