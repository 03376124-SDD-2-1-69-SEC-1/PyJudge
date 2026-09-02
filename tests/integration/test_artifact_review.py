"""Integration tests for transactional artifact review operations."""

import pytest
from sqlalchemy.exc import IntegrityError

from greader.ai.demo import DemoAssignmentGenerator
from greader.ai.errors import ArtifactReviewError
from greader.ai.models import ArtifactStatus
from greader.ai.repository import SqlAlchemyGenerationRepository
from greader.ai.review import ArtifactReviewService
from greader.ai.schemas import GenerationMode
from greader.ai.service import AssignmentGenerationService
from greader.assignments.models import (
    Assignment,
    Difficulty,
    ReviewStatus,
    TestCase,
    TestCaseCategory,
)
from greader.assignments.sql_repository import SqlAlchemyAssignmentRepository
from greader.db_models import GenerationArtifactRecord


def _assignment(*, test_cases: list[TestCase] | None = None) -> Assignment:
    return Assignment(
        id="assignment-1",
        title="Sum Two Numbers",
        description="Read two integers and print their sum.",
        constraints="Inputs fit in a signed 32-bit integer.",
        difficulty=Difficulty.EASY,
        programming_language="Python",
        status="Draft",
        reference_solution="a, b = map(int, input().split())\nprint(a + b)",
        input_format="Two space-separated integers.",
        output_format="One integer: their sum.",
        test_cases=test_cases or [],
    )


def _services(test_session_factory):
    assignments = SqlAlchemyAssignmentRepository(test_session_factory)
    artifacts = SqlAlchemyGenerationRepository(test_session_factory)
    generation = AssignmentGenerationService(
        assignment_repository=assignments,
        generation_repository=artifacts,
        generator=DemoAssignmentGenerator(),
    )
    review = ArtifactReviewService(generation_repository=artifacts)
    return assignments, generation, review


def test_applying_full_artifact_creates_draft_assignment_atomically(
    test_session_factory,
) -> None:
    assignments, generation, review = _services(test_session_factory)
    artifact = generation.generate(
        prompt="Create an arithmetic assignment.",
        mode=GenerationMode.FULL_ASSIGNMENT,
        assignment_id=None,
    )

    result = review.apply_artifact(artifact.id, selected_indexes=[])
    saved = assignments.get_assignment(result.assignment_id)

    assert saved is not None
    assert saved.title == "Sum Two Integers"
    assert saved.status == "Draft"
    assert len(saved.test_cases) == 3
    assert all(case.status is ReviewStatus.PENDING for case in saved.test_cases)
    assert result.saved_count == 3
    with test_session_factory() as session:
        record = session.get(GenerationArtifactRecord, artifact.id)
        assert record.review_status == ArtifactStatus.APPLIED.value
        assert record.reviewed_at is not None


def test_applied_artifact_cannot_be_applied_twice(test_session_factory) -> None:
    _, generation, review = _services(test_session_factory)
    artifact = generation.generate(
        prompt="Create an arithmetic assignment.",
        mode=GenerationMode.FULL_ASSIGNMENT,
        assignment_id=None,
    )
    review.apply_artifact(artifact.id, selected_indexes=[])

    with pytest.raises(ArtifactReviewError, match="artifact_already_applied"):
        review.apply_artifact(artifact.id, selected_indexes=[])


def test_discarded_artifact_is_retained_and_cannot_be_applied(
    test_session_factory,
) -> None:
    _, generation, review = _services(test_session_factory)
    artifact = generation.generate(
        prompt="Create an arithmetic assignment.",
        mode=GenerationMode.FULL_ASSIGNMENT,
        assignment_id=None,
    )

    review.discard_artifact(artifact.id)

    with test_session_factory() as session:
        record = session.get(GenerationArtifactRecord, artifact.id)
        assert record.review_status == ArtifactStatus.DISCARDED.value
        assert record.reviewed_at is not None
    with pytest.raises(ArtifactReviewError, match="artifact_discarded"):
        review.apply_artifact(artifact.id, selected_indexes=[])


def test_selected_test_cases_skip_normalized_duplicates(test_session_factory) -> None:
    assignments, generation, review = _services(test_session_factory)
    assignments.save_assignment(
        _assignment(
            test_cases=[
                TestCase(
                    id="existing-case",
                    assignment_id="assignment-1",
                    input_data="1 4  \r\n\r\n",
                    expected_output="5  \r\n",
                    category=TestCaseCategory.NORMAL,
                    status=ReviewStatus.APPROVED,
                    explanation="Existing approved case.",
                )
            ]
        )
    )
    artifact = generation.generate(
        prompt="Generate test cases.",
        mode=GenerationMode.TEST_CASES,
        assignment_id="assignment-1",
    )

    result = review.apply_artifact(artifact.id, selected_indexes=[0, 1])
    saved = assignments.get_assignment("assignment-1")

    assert result.selected_count == 2
    assert result.saved_count == 1
    assert result.duplicate_count == 1
    assert saved is not None
    assert len(saved.test_cases) == 2
    assert saved.test_cases[0].status is ReviewStatus.APPROVED
    assert saved.test_cases[1].status is ReviewStatus.PENDING


def test_test_case_artifact_requires_a_selection(test_session_factory) -> None:
    assignments, generation, review = _services(test_session_factory)
    assignments.save_assignment(_assignment())
    artifact = generation.generate(
        prompt="Generate test cases.",
        mode=GenerationMode.TEST_CASES,
        assignment_id="assignment-1",
    )

    with pytest.raises(ArtifactReviewError, match="no_test_cases_selected"):
        review.apply_artifact(artifact.id, selected_indexes=[])


def test_failed_assignment_insert_leaves_artifact_as_draft(
    test_session_factory,
) -> None:
    assignments, generation, _ = _services(test_session_factory)
    assignments.save_assignment(_assignment())
    artifact = generation.generate(
        prompt="Create an arithmetic assignment.",
        mode=GenerationMode.FULL_ASSIGNMENT,
        assignment_id=None,
    )
    artifacts = SqlAlchemyGenerationRepository(test_session_factory)

    with pytest.raises(IntegrityError):
        artifacts.apply_full_assignment(artifact.id, _assignment())

    with test_session_factory() as session:
        record = session.get(GenerationArtifactRecord, artifact.id)
        assert record.review_status == ArtifactStatus.DRAFT.value
        assert record.reviewed_at is None
