"""Ports the generation use case needs: the AI client and the persistence store.

`ai/client.py` satisfies `GenerationClient`, with a stub today and an HTTP
adapter later (OPS-04). `database/core/generation_repository.py` provides the
SQL adapter for `GenerationRepository` and `tests/fakes/generation.py` the
in-memory one. Nothing in `core/` may import any of them; only `main.py`
wires them in.
"""

from typing import Protocol

from greader.core.generation.models import AssignmentDraft, Citation, GenerationArtifact
from greader.core.generation.schemas import GenerationRequest, GenerationResponse


class GenerationClient(Protocol):
    """Boundary to whatever produces an Assignment draft from a prompt."""

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Return a draft and its supporting citations."""
        ...


class GenerationRepository(Protocol):
    """Persistence operations required by GenerationService.

    A request and its artifact are tracked as separate rows because a request
    can fail before ever producing one. `create_request` is the only
    operation allowed to assign a request its id, and `create_artifact` is the
    only one allowed to assign an artifact its id -- callers must always use
    the returned value, never a guess at what it will be.
    """

    def create_request(self, prompt: str, filters: dict[str, object]) -> int:
        """Insert a pending request row and return its generated id."""
        ...

    def mark_request_completed(self, request_id: int) -> None:
        """Mark a request as completed."""
        ...

    def mark_request_failed(self, request_id: int, error_code: str) -> None:
        """Mark a request as failed, recording why."""
        ...

    def create_artifact(
        self, request_id: int, draft: AssignmentDraft, citations: list[Citation]
    ) -> GenerationArtifact:
        """Insert an artifact linked to `request_id` and return it with an id."""
        ...

    def get(self, artifact_id: int) -> GenerationArtifact | None:
        """Return an artifact by id when present."""
        ...
