"""Manual Gemini smoke test for Task 5.

Run explicitly:
AI_PROVIDER=gemini GEMINI_API_KEY="your-development-key" \
uv run python -m greader.scripts.gemini_smoke_test
"""

from __future__ import annotations

from greader.assistant.errors import GenerationError
from greader.assistant.interface import GenerationRequest
from greader.assistant.providers import build_assignment_generator
from greader.assistant.schemas import FullAssignmentDraft, GenerationMode
from greader.config import Settings


def main() -> None:
    """Generate one small assignment and print only safe summary data."""
    settings = Settings()
    try:
        generator = build_assignment_generator(settings)
        result = generator.generate(
            GenerationRequest(
                prompt=(
                    "Create a tiny Python stdin/stdout assignment about adding two "
                    "integers."
                ),
                mode=GenerationMode.FULL_ASSIGNMENT,
            ),
            None,
        )
    except GenerationError as exc:
        raise SystemExit(f"Gemini smoke test failed: {exc.safe_error_code}") from None

    if not isinstance(result.payload, FullAssignmentDraft):
        raise RuntimeError("Gemini returned an unexpected payload shape")
    print(f"Title: {result.payload.title}")
    print(f"Generated tests: {len(result.payload.test_cases)}")


if __name__ == "__main__":
    main()
