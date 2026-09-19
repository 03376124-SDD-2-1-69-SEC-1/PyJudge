"""Generation use cases, independent from HTTP and persistence technology."""

from __future__ import annotations

from greader.core.generation.models import (
    AssignmentDraft,
    Citation,
    GenerationArtifact,
    TestCaseDraft,
)
from greader.core.generation.ports import GenerationClient, GenerationRepository
from greader.core.generation.schemas import AssignmentDraft as DraftSchema
from greader.core.generation.schemas import Citation as CitationSchema
from greader.core.generation.schemas import GenerationRequest


class GenerationFailedError(Exception):
    """Raised when the generation client could not produce a draft."""


class GenerationArtifactNotFoundError(Exception):
    """Raised when a requested generation artifact does not exist."""


class GenerationService:
    """Coordinate the generation use case through client and repository seams."""

    def __init__(
        self, repository: GenerationRepository, client: GenerationClient
    ) -> None:
        """Initialize the service with its repository and client seams."""
        self._repository = repository
        self._client = client

    def generate(self, request: GenerationRequest) -> GenerationArtifact:
        """Persist a pending request, call the client, and persist its artifact.

        A request that never gets an artifact is not silently dropped: it is
        left on record as `failed`, with the error code explaining why, and
        the failure is re-raised so the caller knows generation did not happen.
        """
        filters: dict[str, object] = (
            request.filters.model_dump(exclude_none=True)
            if request.filters is not None
            else {}
        )
        request_id = self._repository.create_request(request.prompt, filters)

        try:
            response = self._client.generate(request)
        except Exception as exc:
            self._repository.mark_request_failed(
                request_id, error_code="generation_client_error"
            )
            raise GenerationFailedError from exc

        draft = _to_domain_draft(response.draft)
        citations = [_to_domain_citation(citation) for citation in response.citations]
        artifact = self._repository.create_artifact(request_id, draft, citations)
        self._repository.mark_request_completed(request_id)
        return artifact

    def get(self, artifact_id: int) -> GenerationArtifact:
        """Return one generation artifact or raise when it does not exist."""
        artifact = self._repository.get(artifact_id)
        if artifact is None:
            raise GenerationArtifactNotFoundError
        return artifact


def _to_domain_draft(draft: DraftSchema) -> AssignmentDraft:
    return AssignmentDraft(
        title=draft.title,
        statement=draft.statement,
        test_cases=[
            TestCaseDraft(
                input_data=test_case.input_data,
                expected_output=test_case.expected_output,
                is_hidden=test_case.is_hidden,
                order_index=test_case.order_index,
            )
            for test_case in draft.test_cases
        ],
    )


def _to_domain_citation(citation: CitationSchema) -> Citation:
    return Citation(
        chunk_id=citation.chunk_id,
        source_id=citation.source_id,
        page=citation.page,
        score=citation.score,
        text_snapshot=citation.text_snapshot,
    )
