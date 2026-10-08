"""Adapters satisfying core.generation's GenerationClient Protocol.

StubGenerationClient is kept for demo mode and CI (no API key needed).
OpenRouterGenerationClient is the production adapter: it calls any model
available on OpenRouter through the OpenAI-compatible /chat/completions
endpoint and returns a structured GenerationResponse.

AI-06: citations are returned as [] until AI-05 (retrieval) is wired in.
       expected_output in each TestCaseDraft is "" until CORE-17 (CodeRunner)
       is wired in — the Instructor fills it in at the T-04 stepper.
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI, OpenAIError

from questly.core.generation.schemas import (
    AssignmentDraft,
    Citation,
    GenerationRequest,
    GenerationResponse,
    TestCaseDraft,
)

logger = logging.getLogger(__name__)

_MAX_RETRIES = 4
_TIMEOUT_SECONDS = 60.0

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
  ]
}

Rules:
- Write at least 2 test cases, at most 5.
- "input_data" must be a string of lines exactly as the program would \
read from stdin.
- Do NOT include "expected_output" — leave it to the instructor.
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
    - expected_output in every TestCaseDraft is "" until CORE-17 is done.
    - Any JSON parse error or missing key raises, which GenerationService
      catches as GenerationFailedError (T-03d).
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
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
        return _parse_response(raw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> GenerationResponse:
    """Parse the LLM's JSON reply into a GenerationResponse.

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
            expected_output="",  # filled by instructor at T-04; CORE-17 will automate
        )
        for tc in raw_cases
        if isinstance(tc, dict)
    ]

    if not test_cases:
        raise ValueError(f"LLM returned no usable test cases. Got: {raw_cases!r}")

    draft = AssignmentDraft(
        title=title.strip(), statement=statement.strip(), test_cases=test_cases
    )
    # Citations are empty until AI-05 (retrieval) is wired in.
    return GenerationResponse(draft=draft, citations=[])
