"""Integration tests for persisted assignment-generation artifacts."""

import json

import pytest

from greader.assignments.models import Assignment, Difficulty
from greader.assignments.repository import InMemoryAssignmentRepository
from greader.assistant.demo import DemoAssignmentGenerator
from greader.assistant.errors import GenerationError
from greader.assistant.repository import SqlAlchemyGenerationRepository
from greader.assistant.schemas import GenerationMode
from greader.assistant.service import AssignmentGenerationService
from greader.db_models import GenerationArtifactRecord, GenerationRequestRecord


def _assignment() -> Assignment:
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
    )


def _service(test_session_factory, assignment_repo=None, generator=None):
    return AssignmentGenerationService(
        assignment_repository=assignment_repo or InMemoryAssignmentRepository(),
        generation_repository=SqlAlchemyGenerationRepository(test_session_factory),
        generator=generator or DemoAssignmentGenerator(),
    )


def test_successful_generation_persists_request_and_validated_artifact(
    test_session_factory,
) -> None:
    artifact = _service(test_session_factory).generate(
        prompt="  Generate a small arithmetic assignment.  ",
        mode=GenerationMode.FULL_ASSIGNMENT,
        assignment_id=None,
    )

    with test_session_factory() as session:
        request = session.get(GenerationRequestRecord, artifact.generation_request_id)
        stored_artifact = session.get(GenerationArtifactRecord, artifact.id)

    assert request is not None
    assert request.status == "succeeded"
    assert request.prompt == "Generate a small arithmetic assignment."
    assert request.completed_at is not None
    assert stored_artifact is not None
    assert stored_artifact.generation_mode == GenerationMode.FULL_ASSIGNMENT.value
    assert stored_artifact.is_applied is False
    assert json.loads(stored_artifact.payload_json)["title"] == artifact.payload.title


@pytest.mark.parametrize("mode", [GenerationMode.TEST_CASES, GenerationMode.EDGE_CASES])
def test_context_modes_require_an_existing_assignment(
    test_session_factory, mode
) -> None:
    service = _service(test_session_factory)

    with pytest.raises(GenerationError, match="assignment_required"):
        service.generate(prompt="Generate tests.", mode=mode, assignment_id=None)


def test_context_modes_load_selected_assignment(test_session_factory) -> None:
    assignments = InMemoryAssignmentRepository()
    assignments.save_assignment(_assignment())
    artifact = _service(test_session_factory, assignment_repo=assignments).generate(
        prompt="Generate test cases.",
        mode=GenerationMode.TEST_CASES,
        assignment_id="assignment-1",
    )

    assert "Sum Two Numbers" in artifact.summary
    assert artifact.mode is GenerationMode.TEST_CASES


class _FailingGenerator:
    def generate(self, request, assignment):
        raise GenerationError("provider_rate_limited")


def test_failed_generation_persists_safe_error_without_artifact(
    test_session_factory,
) -> None:
    service = _service(test_session_factory, generator=_FailingGenerator())

    with pytest.raises(GenerationError, match="provider_rate_limited"):
        service.generate(
            prompt="Generate an assignment.",
            mode=GenerationMode.FULL_ASSIGNMENT,
            assignment_id=None,
        )

    with test_session_factory() as session:
        requests = session.query(GenerationRequestRecord).all()
        artifacts = session.query(GenerationArtifactRecord).all()

    assert len(requests) == 1
    assert requests[0].status == "failed"
    assert requests[0].safe_error_code == "provider_rate_limited"
    assert requests[0].completed_at is not None
    assert artifacts == []
