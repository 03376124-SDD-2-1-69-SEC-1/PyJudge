"""Adapters satisfying core.generation's GenerationClient Protocol.

StubGenerationClient is kept for demo mode and CI (no API key needed).
OpenRouterGenerationClient is the production adapter: it calls any model
available on OpenRouter through the OpenAI-compatible /chat/completions
endpoint and returns a structured GenerationResponse.

Citations are returned as [] until AI-05 (retrieval) is wired in. The LLM
writes a reference solution but never the expected outputs: each test case's
expected_output is that solution's stdout from the CodeRunner, or "" when the
run fails (always, under the stub runner) and the Instructor fills it at T-04.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI, OpenAIError

from questly.core.generation.schemas import (
    AssignmentDraft,
    Citation,
    GenerationRequest,
    GenerationResponse,
    TestCaseDraft,
)
from questly.core.submissions.models import ExecutionStatus
from questly.core.submissions.ports import CodeRunner

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_TIMEOUT_SECONDS = 60.0
_SOLUTION_LANGUAGE = "python"
_SOLUTION_TIME_LIMIT_SECONDS = 5.0

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an assistant that creates programming assignment drafts for a \
computer science course management system.

Given a prompt describing the programming problem, respond with ONLY a \
JSON object (no markdown, no explanation) in this exact shape:

{
  "title": "<short assignment title>",
  "statement": "<full problem statement in the same language as the prompt>",
  "test_cases": [
    {"input_data": "<sample input>"},
    {"input_data": "<another sample input>"}
  ],
  "reference_solution": "<complete Python 3 program that solves the problem>"
}

Rules:
- Write at least 2 test cases, at most 5.
- "input_data" must be a string of lines exactly as the program would \
read from stdin.
- "reference_solution" must be a complete Python 3 program that reads the \
input from stdin and prints the answer to stdout, nothing else.
- Do NOT include "expected_output" — it is computed by running \
"reference_solution" on each input.
- Do NOT include markdown fences or any text outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


class StubGenerationClient:
    """Returns a hardcoded draft regardless of the request.

    Used in demo mode and in tests that do not have an API key.
    """

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return a fixed draft and citation so the endpoint is callable end to end."""
        draft = AssignmentDraft(
            title="Sample Assignment",
            statement=f"Stub draft generated for prompt: {request.prompt}",
            test_cases=[
                TestCaseDraft(input_data="1 2", expected_output="3"),
            ],
        )
        citation = Citation(
            chunk_id=1,
            source_id=1,
            page=1,
            score=1.0,
            text_snapshot="stub citation text",
        )
        return GenerationResponse(draft=draft, citations=[citation])


class OpenRouterGenerationClient:
    """Production adapter: calls OpenRouter via the OpenAI-compatible API.

    - Citations are [] until AI-05 (retrieval) is wired in.
    - expected_output is the reference solution's stdout from the CodeRunner;
      a failed run, or a reply without a solution, leaves it "" for the
      Instructor and never fails the generation.
    - Any JSON parse error or missing key raises, which GenerationService
      catches as GenerationFailedError (T-03d).
    """

    def __init__(self, api_key: str, model: str, code_runner: CodeRunner) -> None:
        self._model = model
        self._code_runner = code_runner
        # The SDK retries 429 and 5xx with exponential backoff and honours
        # Retry-After; free models hit transient upstream 429s often.
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            max_retries=_MAX_RETRIES,
            timeout=_TIMEOUT_SECONDS,
        )

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Call the LLM and parse a structured GenerationResponse."""
        user_content = request.prompt
        if request.filters and request.filters.difficulty:
            user_content += f"\n\nDifficulty level: {request.filters.difficulty}"

        logger.debug("OpenRouterGenerationClient.generate model=%s", self._model)

        try:
            completion = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            )
        except OpenAIError:
            # GenerationService turns every client failure into one generic
            # GenerationFailedError, so this is the only place the cause is seen.
            logger.exception("OpenRouter call failed model=%s", self._model)
            raise

        raw = completion.choices[0].message.content or ""
        return self._with_expected_outputs(_parse_response(raw))

    def _with_expected_outputs(self, parsed: _ParsedReply) -> GenerationResponse:
        draft = parsed.response.draft
        if not parsed.reference_solution:
            logger.warning(
                "LLM reply has no reference_solution model=%s; "
                "expected outputs left blank",
                self._model,
            )
            return parsed.response

        test_cases = []
        for index, test_case in enumerate(draft.test_cases):
            execution = self._code_runner.run(
                code=parsed.reference_solution,
                language=_SOLUTION_LANGUAGE,
                stdin=test_case.input_data,
                time_limit_seconds=_SOLUTION_TIME_LIMIT_SECONDS,
            )
            if execution.status is ExecutionStatus.OK:
                expected_output = _as_expected_output(execution.stdout)
            else:
                logger.warning(
                    "reference solution failed model=%s test_case=%d status=%s; "
                    "expected output left blank",
                    self._model,
                    index,
                    execution.status.value,
                )
                expected_output = ""
            test_cases.append(
                test_case.model_copy(update={"expected_output": expected_output})
            )

        return parsed.response.model_copy(
            update={"draft": draft.model_copy(update={"test_cases": test_cases})}
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ParsedReply:
    """The draft as the LLM wrote it, plus the solution that stays in the client.

    `reference_solution` is "" when the reply has no usable one.
    """

    response: GenerationResponse
    reference_solution: str


def _as_expected_output(stdout: str) -> str:
    """Stdout in the form SubmissionService.outputs_match compares on."""
    return "\n".join(line.rstrip() for line in stdout.rstrip().splitlines())


def _parse_response(raw: str) -> _ParsedReply:
    """Parse the LLM's JSON reply.

    Raises ValueError (caught upstream as GenerationFailedError) if the
    response is not valid JSON or is missing required keys.
    """
    # Strip accidental markdown fences the model may produce despite the prompt
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop opening fence (```json or ```) and closing fence (```)
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM response is not valid JSON: {exc}\nRaw: {raw!r}"
        ) from exc

    title = data.get("title")
    statement = data.get("statement")
    raw_cases = data.get("test_cases")

    if not title or not isinstance(title, str):
        raise ValueError(f"LLM response missing 'title'. Got: {data!r}")
    if not statement or not isinstance(statement, str):
        raise ValueError(f"LLM response missing 'statement'. Got: {data!r}")
    if raw_cases is None or not isinstance(raw_cases, list):
        raise ValueError(f"LLM response missing 'test_cases'. Got: {data!r}")

    test_cases = [
        TestCaseDraft(
            input_data=str(tc.get("input_data", "")),
            expected_output="",
        )
        for tc in raw_cases
        if isinstance(tc, dict)
    ]

    if not test_cases:
        raise ValueError(f"LLM returned no usable test cases. Got: {raw_cases!r}")

    draft = AssignmentDraft(
        title=title.strip(), statement=statement.strip(), test_cases=test_cases
    )
    solution = data.get("reference_solution")
    if not isinstance(solution, str) or not solution.strip():
        solution = ""
    # Citations are empty until AI-05 (retrieval) is wired in.
    return _ParsedReply(
        response=GenerationResponse(draft=draft, citations=[]),
        reference_solution=solution,
    )
