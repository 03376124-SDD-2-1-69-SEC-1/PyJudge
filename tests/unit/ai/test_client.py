"""Tests for generation client adapters.

StubGenerationClient tests remain as-is (regression guard).
OpenRouterGenerationClient tests use monkeypatch to avoid real HTTP calls.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import httpx
import openrouter.utils.retries
import pytest
from openrouter.errors import NoResponseError, OpenRouterError

from questly.ai.client import (
    OpenRouterGenerationClient,
    StubGenerationClient,
    _parse_response,
)
from questly.core.generation.schemas import GenerationRequest, GenerationResponse
from questly.core.submissions.models import Execution, ExecutionStatus

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
    parsed = _parse_response(raw)
    response = parsed.response

    assert response.draft.title == "Two Sum"
    assert "array" in response.draft.statement
    assert len(response.draft.test_cases) == 2
    # the parser never trusts the LLM for outputs; the CodeRunner fills them
    assert all(tc.expected_output == "" for tc in response.draft.test_cases)
    # citations empty until AI-05
    assert response.citations == []


def test_parse_response_carries_reference_solution() -> None:
    raw = (
        '{"title": "T", "statement": "S", "test_cases": [{"input_data": "1"}],'
        ' "reference_solution": "print(int(input()) + 1)"}'
    )
    assert _parse_response(raw).reference_solution == "print(int(input()) + 1)"


def test_parse_response_strips_markdown_fence() -> None:
    raw = (
        "```json\n"
        '{"title": "X", "statement": "Y", "test_cases": [{"input_data": "1"}]}\n'
        "```"
    )
    assert _parse_response(raw).response.draft.title == "X"


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


class FakeCodeRunner:
    """Satisfies CodeRunner: records each call and replays scripted Executions."""

    def __init__(self, executions: list[Execution]) -> None:
        self._executions = list(executions)
        self.calls: list[tuple[str, str, str]] = []

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution:
        self.calls.append((code, language, stdin))
        return self._executions.pop(0)


def _ok(stdout: str) -> Execution:
    return Execution(
        status=ExecutionStatus.OK, stdout=stdout, stderr="", time_seconds=0.01
    )


def _failed(status: ExecutionStatus) -> Execution:
    return Execution(status=status, stdout="partial", stderr="boom", time_seconds=5.0)


def _make_client(
    model: str = "test/model", code_runner: FakeCodeRunner | None = None
) -> OpenRouterGenerationClient:
    """Build a client with a dummy key; SDK won't validate until a call is made."""
    if code_runner is None:
        code_runner = FakeCodeRunner([_ok("5"), _ok("42")])
    return OpenRouterGenerationClient(
        api_key="dummy-key", model=lambda: model, code_runner=code_runner
    )


def _mock_result(content: str) -> MagicMock:
    """Return a mock that looks like openrouter.components.ChatResult."""
    choice = MagicMock()
    choice.message.content = content
    result = MagicMock()
    result.choices = [choice]
    return result


_SOLUTION = "n = int(input())\nprint(max(map(int, input().split())))"

_VALID_LLM_RESPONSE = json.dumps(
    {
        "title": "Find Maximum",
        "statement": "Given N integers, find the maximum.",
        "test_cases": [{"input_data": "3\n1 5 2"}, {"input_data": "1\n42"}],
        "reference_solution": _SOLUTION,
    }
)

_NO_SOLUTION_LLM_RESPONSE = """{
    "title": "Find Maximum",
    "statement": "Given N integers, find the maximum.",
    "test_cases": [
        {"input_data": "3\\n1 5 2"},
        {"input_data": "1\\n42"}
    ]
}"""


def _generate(client: OpenRouterGenerationClient, llm_reply: str) -> GenerationResponse:
    with patch.object(
        client._client.chat,
        "send",
        return_value=_mock_result(llm_reply),
    ):
        return client.generate(GenerationRequest(prompt="find max"))


def test_openrouter_client_reads_the_model_on_every_call() -> None:
    """An Admin's A-01 model change reaches the next generation."""
    chosen = ["first/model"]
    client = OpenRouterGenerationClient(
        api_key="dummy-key",
        model=lambda: chosen[0],
        code_runner=FakeCodeRunner([_ok("5"), _ok("42"), _ok("5"), _ok("42")]),
    )

    with patch.object(
        client._client.chat,
        "send",
        return_value=_mock_result(_VALID_LLM_RESPONSE),
    ) as create:
        client.generate(GenerationRequest(prompt="find max"))
        chosen[0] = "second/model"
        client.generate(GenerationRequest(prompt="find max"))

    assert [call.kwargs["model"] for call in create.call_args_list] == [
        "first/model",
        "second/model",
    ]


def test_openrouter_client_returns_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client()

    with patch.object(
        client._client.chat,
        "send",
        return_value=_mock_result(_VALID_LLM_RESPONSE),
    ):
        response = client.generate(GenerationRequest(prompt="find max in array"))

    assert response.draft.title == "Find Maximum"
    assert len(response.draft.test_cases) == 2


def test_openrouter_client_runs_reference_solution_on_each_input() -> None:
    runner = FakeCodeRunner([_ok("5\n"), _ok("42\n")])

    _generate(_make_client(code_runner=runner), _VALID_LLM_RESPONSE)

    assert runner.calls == [
        (_SOLUTION, "python", "3\n1 5 2"),
        (_SOLUTION, "python", "1\n42"),
    ]


def test_openrouter_client_expected_output_is_runner_stdout() -> None:
    runner = FakeCodeRunner([_ok("5  \nx\n\n"), _ok("42\n")])

    response = _generate(_make_client(code_runner=runner), _VALID_LLM_RESPONSE)

    # stored the way SubmissionService.outputs_match normalises a run's stdout
    assert [tc.expected_output for tc in response.draft.test_cases] == ["5\nx", "42"]


@pytest.mark.parametrize(
    "status", [ExecutionStatus.RUNTIME_ERROR, ExecutionStatus.TIME_LIMIT]
)
def test_openrouter_client_failed_run_leaves_that_output_blank(
    status: ExecutionStatus, caplog: pytest.LogCaptureFixture
) -> None:
    runner = FakeCodeRunner([_failed(status), _ok("42\n")])

    with caplog.at_level(logging.WARNING, logger="questly.ai.client"):
        response = _generate(
            _make_client(model="some/model", code_runner=runner), _VALID_LLM_RESPONSE
        )

    assert [tc.expected_output for tc in response.draft.test_cases] == ["", "42"]
    assert "some/model" in caplog.text
    assert status.value in caplog.text
    assert _SOLUTION not in caplog.text


@pytest.mark.parametrize(
    "solution_field", ["", ', "reference_solution": ""', ', "reference_solution": 7']
)
def test_openrouter_client_without_solution_skips_runner(
    solution_field: str, caplog: pytest.LogCaptureFixture
) -> None:
    runner = FakeCodeRunner([_ok("5"), _ok("42")])
    reply = _NO_SOLUTION_LLM_RESPONSE.rstrip().removesuffix("}") + solution_field + "}"

    with caplog.at_level(logging.WARNING, logger="questly.ai.client"):
        response = _generate(_make_client(code_runner=runner), reply)

    assert [tc.expected_output for tc in response.draft.test_cases] == ["", ""]
    assert runner.calls == []
    assert len(caplog.records) == 1


def test_openrouter_client_citations_are_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client()

    with patch.object(
        client._client.chat,
        "send",
        return_value=_mock_result(_VALID_LLM_RESPONSE),
    ):
        response = client.generate(GenerationRequest(prompt="find max"))

    assert response.citations == []


def _chat_result_json(content: str) -> dict[str, object]:
    return {
        "id": "gen-1",
        "object": "chat.completion",
        "created": 1,
        "model": "test/model",
        "system_fingerprint": None,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


def test_openrouter_client_retries_a_rate_limit_then_parses_the_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Free models return transient 429s; the SDK alone retries only 5XX."""
    monkeypatch.setattr(openrouter.utils.retries.time, "sleep", lambda _s: None)
    requests: list[httpx.Request] = []

    def reply(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, json={"error": {"code": 429, "message": "x"}})
        return httpx.Response(200, json=_chat_result_json(_VALID_LLM_RESPONSE))

    client = _make_client(model="some/model:free")
    client._client.sdk_configuration.client = httpx.Client(
        transport=httpx.MockTransport(reply)
    )

    response = client.generate(GenerationRequest(prompt="find max"))

    assert response.draft.title == "Find Maximum"
    assert len(requests) == 2
    assert requests[-1].url == "https://openrouter.ai/api/v1/chat/completions"
    body = json.loads(requests[-1].content)
    assert body["model"] == "some/model:free"
    assert [message["role"] for message in body["messages"]] == ["system", "user"]


@pytest.mark.parametrize(
    "error",
    [
        OpenRouterError(
            "429 rate limited",
            httpx.Response(429, request=httpx.Request("POST", "https://x")),
        ),
        NoResponseError("429 rate limited"),
        httpx.ReadTimeout("429 rate limited"),
    ],
    ids=["openrouter-error", "no-response", "timeout"],
)
def test_openrouter_client_logs_and_reraises_api_failure(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    """The service hides the cause, so the client must log it."""
    client = _make_client(model="some/model:free")

    with (
        patch.object(client._client.chat, "send", side_effect=error),
        caplog.at_level(logging.ERROR, logger="questly.ai.client"),
        pytest.raises(type(error)),
    ):
        client.generate(GenerationRequest(prompt="anything"))

    assert "some/model:free" in caplog.text
    assert "429 rate limited" in caplog.text


def test_openrouter_client_bad_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM returning garbage → ValueError → GenerationService catches it."""
    client = _make_client()

    with (
        patch.object(
            client._client.chat,
            "send",
            return_value=_mock_result("oops not json"),
        ),
        pytest.raises(ValueError),
    ):
        client.generate(GenerationRequest(prompt="anything"))
