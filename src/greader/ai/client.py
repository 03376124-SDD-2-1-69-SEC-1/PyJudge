"""Adapters satisfying core.generation's GenerationClient Protocol.

StubGenerationClient is a placeholder. OPS-04 replaces it with an adapter
that calls the ai repo over HTTP; routes.py and the Protocol do not change
when that happens.
"""

from greader.core.generation.schemas import (
    AssignmentDraft,
    Citation,
    GenerationRequest,
    GenerationResponse,
    TestCaseDraft,
)


class StubGenerationClient:
    """Returns a hardcoded draft regardless of the request."""

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
