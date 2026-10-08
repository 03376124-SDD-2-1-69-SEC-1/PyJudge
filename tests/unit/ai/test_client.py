"""Tests for generation client adapters.

StubGenerationClient tests remain as-is (regression guard).
OpenRouterGenerationClient tests use monkeypatch to avoid real HTTP calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from questly.ai.client import (
    OpenRouterGenerationClient,
    StubGenerationClient,
    _parse_response,
)
from questly.core.generation.schemas import GenerationRequest

# ---------------------------------------------------------------------------
# StubGenerationClient — kept as regression guard
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# _parse_response helper
# ---------------------------------------------------------------------------


def test_parse_response_valid_json() -> None:
    raw = """{
        "title": "Two Sum",
        "statement": "Given an array, find two numbers that add up to target.",
        "test_cases": [
            {"input_data": "4 2\\n1 3"},
            {"input_data": "3 1\\n0 1"}
        ]
    }"""
    response = _parse_response(raw)

    assert response.draft.title == "Two Sum"
    assert "array" in response.draft.statement
    assert len(response.draft.test_cases) == 2
    # expected_output is always blank — instructor fills at T-04
    assert all(tc.expected_output == "" for tc in response.draft.test_cases)
    # citations empty until AI-05
    assert response.citations == []


def test_parse_response_strips_markdown_fence() -> None:
    raw = (
        "```json\n"
        '{"title": "X", "statement": "Y", "test_cases": [{"input_data": "1"}]}\n'
        "```"
    )
    response = _parse_response(raw)
    assert response.draft.title == "X"


def test_parse_response_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="not valid JSON"):
        _parse_response("not json at all")


def test_parse_response_missing_title_raises() -> None:
    raw = '{"statement": "S", "test_cases": [{"input_data": "1"}]}'
    with pytest.raises(ValueError, match="missing 'title'"):
        _parse_response(raw)


def test_parse_response_missing_statement_raises() -> None:
    raw = '{"title": "T", "test_cases": [{"input_data": "1"}]}'
    with pytest.raises(ValueError, match="missing 'statement'"):
        _parse_response(raw)


def test_parse_response_empty_test_cases_raises() -> None:
    raw = '{"title": "T", "statement": "S", "test_cases": []}'
    with pytest.raises(ValueError, match="no usable test cases"):
        _parse_response(raw)


# ---------------------------------------------------------------------------
# OpenRouterGenerationClient — monkeypatched, no real HTTP
# ---------------------------------------------------------------------------


def _make_client(model: str = "test/model") -> OpenRouterGenerationClient:
    """Build a client with a dummy key; SDK won't validate until a call is made."""
    return OpenRouterGenerationClient(api_key="dummy-key", model=model)


def _mock_completion(content: str) -> MagicMock:
    """Return a mock that looks like openai.types.chat.ChatCompletion."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


_VALID_LLM_RESPONSE = """{
    "title": "Find Maximum",
    "statement": "Given N integers, find the maximum.",
    "test_cases": [
        {"input_data": "3\\n1 5 2"},
        {"input_data": "1\\n42"}
    ]
}"""


def test_openrouter_client_returns_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client()

    with patch.object(
        client._client.chat.completions,
        "create",
        return_value=_mock_completion(_VALID_LLM_RESPONSE),
    ):
        response = client.generate(GenerationRequest(prompt="find max in array"))

    assert response.draft.title == "Find Maximum"
    assert len(response.draft.test_cases) == 2


def test_openrouter_client_expected_output_is_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _make_client()

    with patch.object(
        client._client.chat.completions,
        "create",
        return_value=_mock_completion(_VALID_LLM_RESPONSE),
    ):
        response = client.generate(GenerationRequest(prompt="find max"))

    assert all(tc.expected_output == "" for tc in response.draft.test_cases)


def test_openrouter_client_citations_are_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client()

    with patch.object(
        client._client.chat.completions,
        "create",
        return_value=_mock_completion(_VALID_LLM_RESPONSE),
    ):
        response = client.generate(GenerationRequest(prompt="find max"))

    assert response.citations == []


def test_openrouter_client_bad_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM returning garbage → ValueError → GenerationService catches it."""
    client = _make_client()

    with (
        patch.object(
            client._client.chat.completions,
            "create",
            return_value=_mock_completion("oops not json"),
        ),
        pytest.raises(ValueError),
    ):
        client.generate(GenerationRequest(prompt="anything"))
