"""Unit tests for structured assignment generation providers and schemas."""

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
from pydantic import ValidationError

from greader.assignments.models import Assignment, Difficulty
from greader.assistant.demo import DemoAssignmentGenerator
from greader.assistant.errors import GeminiConfigurationError, GenerationError
from greader.assistant.gemini import GeminiAssignmentGenerator
from greader.assistant.interface import GenerationRequest
from greader.assistant.providers import ai_connection_status, build_assignment_generator
from greader.assistant.schemas import (
    FullAssignmentDraft,
    GenerationMode,
    TestCaseDraftSet,
)
from greader.config import Settings


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


@pytest.mark.parametrize(
    ("mode", "expected_type"),
    [
        (GenerationMode.FULL_ASSIGNMENT, FullAssignmentDraft),
        (GenerationMode.TEST_CASES, TestCaseDraftSet),
        (GenerationMode.EDGE_CASES, TestCaseDraftSet),
    ],
)
def test_demo_provider_returns_deterministic_valid_payload_for_each_mode(
    mode: GenerationMode, expected_type: type[FullAssignmentDraft | TestCaseDraftSet]
) -> None:
    assignment = _assignment() if mode is not GenerationMode.FULL_ASSIGNMENT else None
    request = GenerationRequest(
        prompt="  Create a short arithmetic assignment.  ",
        mode=mode,
        assignment_id=assignment.id if assignment else None,
    )

    result = DemoAssignmentGenerator().generate(request, assignment)

    assert (
        result.payload
        == DemoAssignmentGenerator().generate(request, assignment).payload
    )
    assert isinstance(result.payload, expected_type)
    assert result.mode is mode
    assert result.provider == "demo"
    if mode is GenerationMode.EDGE_CASES:
        assert {case.category.value for case in result.payload.test_cases} <= {
            "Boundary",
            "Corner",
            "Stress",
        }
    if assignment is not None:
        assert assignment.title in result.summary


@pytest.mark.parametrize("prompt", ["", "   ", "x" * 4001])
def test_generation_request_rejects_invalid_prompts(prompt: str) -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(prompt=prompt, mode=GenerationMode.FULL_ASSIGNMENT)


def test_generation_request_trims_and_allows_full_assignment_without_context() -> None:
    request = GenerationRequest(
        prompt="  Draft an assignment about sums.  ",
        mode=GenerationMode.FULL_ASSIGNMENT,
    )

    assert request.prompt == "Draft an assignment about sums."
    assert request.assignment_id is None



def test_generated_test_case_requires_expected_output() -> None:
    payload = (
        DemoAssignmentGenerator()
        .generate(
            GenerationRequest(
                prompt="Generate tests.",
                mode=GenerationMode.TEST_CASES,
                assignment_id="assignment-1",
            ),
            _assignment(),
        )
        .payload.model_dump(mode="json")
    )
    payload["test_cases"][0]["expected_output"] = ""

    with pytest.raises(ValidationError):
        TestCaseDraftSet.model_validate(payload)


class _FakeModels:
    def __init__(self, response: object | Exception) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def generate_content(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class _FakeGeminiClient:
    def __init__(self, response: object | Exception) -> None:
        self.models = _FakeModels(response)


def test_gemini_provider_uses_structured_output_and_validates_fake_response() -> None:
    demo_payload = (
        DemoAssignmentGenerator()
        .generate(
            GenerationRequest(
                prompt="Draft an assignment.", mode=GenerationMode.FULL_ASSIGNMENT
            ),
            None,
        )
        .payload.model_dump(mode="json")
    )
    client = _FakeGeminiClient(SimpleNamespace(parsed=demo_payload))
    generator = GeminiAssignmentGenerator(
        api_key="test-key",
        model_name="gemini-test",
        timeout_seconds=7,
        client=client,
    )

    result = generator.generate(
        GenerationRequest(
            prompt="Draft an assignment.", mode=GenerationMode.FULL_ASSIGNMENT
        ),
        None,
    )

    assert isinstance(result.payload, FullAssignmentDraft)
    assert client.models.calls[0]["model"] == "gemini-test"
    assert client.models.calls[0]["config"].response_mime_type == "application/json"


def test_gemini_provider_rejects_malformed_fake_response() -> None:
    client = _FakeGeminiClient(SimpleNamespace(parsed={"title": "bad"}))
    generator = GeminiAssignmentGenerator(api_key="test-key", client=client)

    with pytest.raises(GenerationError, match="provider_invalid_response"):
        generator.generate(
            GenerationRequest(
                prompt="Draft an assignment.", mode=GenerationMode.FULL_ASSIGNMENT
            ),
            None,
        )


def test_gemini_provider_maps_timeout_to_safe_error() -> None:
    generator = GeminiAssignmentGenerator(
        api_key="test-key", client=_FakeGeminiClient(TimeoutError("request timed out"))
    )

    with pytest.raises(GenerationError, match="provider_timeout"):
        generator.generate(
            GenerationRequest(
                prompt="Draft an assignment.", mode=GenerationMode.FULL_ASSIGNMENT
            ),
            None,
        )


@pytest.mark.parametrize(
    ("status_code", "safe_code"),
    [
        (401, "provider_authentication_failed"),
        (403, "provider_authentication_failed"),
        (429, "provider_rate_limited"),
    ],
)
def test_gemini_provider_maps_client_errors_to_safe_codes(
    status_code: int,
    safe_code: str,
) -> None:
    generator = GeminiAssignmentGenerator(
        api_key="test-key",
        client=_FakeGeminiClient(
            genai_errors.ClientError(
                status_code,
                {"error": {"message": "raw provider detail"}},
            )
        ),
    )

    with pytest.raises(GenerationError, match=safe_code):
        generator.generate(
            GenerationRequest(
                prompt="Draft an assignment.",
                mode=GenerationMode.FULL_ASSIGNMENT,
            ),
            None,
        )


def test_gemini_provider_surfaces_no_api_key_in_errors_or_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "secret-value-that-must-not-leak"
    generator = GeminiAssignmentGenerator(
        api_key=secret,
        client=_FakeGeminiClient(RuntimeError(f"{secret} appeared in raw error")),
    )

    with pytest.raises(GenerationError) as error:
        generator.generate(
            GenerationRequest(
                prompt="Draft an assignment.",
                mode=GenerationMode.FULL_ASSIGNMENT,
            ),
            None,
        )

    assert secret not in str(error.value)
    assert secret not in caplog.text


def test_provider_configuration_never_exposes_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "secret-value-that-must-not-leak"
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(GeminiConfigurationError) as error:
        build_assignment_generator(Settings(_env_file=None))

    assert secret not in str(error.value)
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    status = ai_connection_status(Settings(_env_file=None))
    assert status.configured is True
    assert secret not in str(status.model_dump())


def test_demo_provider_is_available_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "demo")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    generator = build_assignment_generator(Settings(_env_file=None))
    status = ai_connection_status(Settings(_env_file=None))

    assert isinstance(generator, DemoAssignmentGenerator)
    assert status == {"provider": "demo", "model_name": "demo", "configured": True}



