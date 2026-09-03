"""Tests for the stub generation client adapter."""

from greader.ai.client import StubGenerationClient
from greader.core.generation.schemas import GenerationRequest


def test_stub_client_returns_draft_with_citations() -> None:
    client = StubGenerationClient()
    request = GenerationRequest(prompt="two-sum problem")

    response = client.generate(request)

    assert response.draft.title
    assert response.draft.test_cases
    assert response.citations


def test_stub_client_echoes_prompt_into_statement() -> None:
    client = StubGenerationClient()
    request = GenerationRequest(prompt="reverse a linked list")

    response = client.generate(request)

    assert "reverse a linked list" in response.draft.statement
