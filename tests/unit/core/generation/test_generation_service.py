"""Tests for Generation application rules."""

import pytest

from greader.ai.client import StubGenerationClient
from greader.core.generation.schemas import GenerationRequest
from greader.core.generation.service import (
    GenerationArtifactNotFoundError,
    GenerationFailedError,
    GenerationService,
)
from tests.fakes.generation import FakeGenerationRepository


class _FailingClient:
    """A GenerationClient double that always raises, for the failure path."""

    def generate(self, request: GenerationRequest) -> None:
        """Raise instead of producing a draft."""
        raise RuntimeError("the AI service is unreachable")


def test_generate_persists_request_and_artifact_and_returns_it() -> None:
    repository = FakeGenerationRepository()
    service = GenerationService(repository, StubGenerationClient())

    artifact = service.generate(GenerationRequest(prompt="write a sorting assignment"))

    assert isinstance(artifact.id, int)
    assert artifact.draft.title
    assert artifact.draft.test_cases
    assert artifact.citations
    assert artifact.review_status == "pending"

    stored_request = repository.requests[1]
    assert stored_request.prompt == "write a sorting assignment"
    assert stored_request.status == "completed"


def test_generate_records_the_submitted_filters() -> None:
    repository = FakeGenerationRepository()
    service = GenerationService(repository, StubGenerationClient())

    service.generate(
        GenerationRequest(
            prompt="write a graph assignment",
            filters={"topic": "graphs", "difficulty": "medium"},
        )
    )

    stored_request = repository.requests[1]
    assert stored_request.filters == {"topic": "graphs", "difficulty": "medium"}


def test_generate_marks_the_request_failed_and_raises_on_client_error() -> None:
    repository = FakeGenerationRepository()
    service = GenerationService(repository, _FailingClient())

    with pytest.raises(GenerationFailedError):
        service.generate(GenerationRequest(prompt="anything"))

    stored_request = repository.requests[1]
    assert stored_request.status == "failed"
    assert stored_request.error_code


def test_get_returns_a_persisted_artifact() -> None:
    repository = FakeGenerationRepository()
    service = GenerationService(repository, StubGenerationClient())
    created = service.generate(GenerationRequest(prompt="graph traversal"))

    fetched = service.get(created.id)

    assert fetched == created


def test_get_missing_artifact_raises() -> None:
    service = GenerationService(FakeGenerationRepository(), StubGenerationClient())

    with pytest.raises(GenerationArtifactNotFoundError):
        service.get(999)
