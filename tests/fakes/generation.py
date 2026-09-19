"""In-memory GenerationRepository, behaviour-matched to the SQL adapter."""

from __future__ import annotations

from dataclasses import dataclass

from greader.core.generation.models import AssignmentDraft, Citation, GenerationArtifact


@dataclass
class StoredGenerationRequest:
    """Bookkeeping for a generation request, exposed for test assertions."""

    prompt: str
    filters: dict[str, object]
    status: str = "pending"
    error_code: str | None = None


class FakeGenerationRepository:
    """Store generation requests and artifacts in process for tests."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self.requests: dict[int, StoredGenerationRequest] = {}
        self._artifacts: dict[int, GenerationArtifact] = {}
        self._next_request_id = 1
        self._next_artifact_id = 1

    def create_request(self, prompt: str, filters: dict[str, object]) -> int:
        """Insert a pending request row and return its generated id."""
        request_id = self._next_request_id
        self._next_request_id += 1
        self.requests[request_id] = StoredGenerationRequest(
            prompt=prompt, filters=dict(filters)
        )
        return request_id

    def mark_request_completed(self, request_id: int) -> None:
        """Mark a request as completed."""
        self.requests[request_id].status = "completed"

    def mark_request_failed(self, request_id: int, error_code: str) -> None:
        """Mark a request as failed, recording why."""
        request = self.requests[request_id]
        request.status = "failed"
        request.error_code = error_code

    def create_artifact(
        self, request_id: int, draft: AssignmentDraft, citations: list[Citation]
    ) -> GenerationArtifact:
        """Insert an artifact linked to `request_id` and return it with an id."""
        artifact_id = self._next_artifact_id
        self._next_artifact_id += 1
        artifact = GenerationArtifact(
            id=artifact_id, draft=draft, citations=list(citations)
        )
        self._artifacts[artifact_id] = artifact
        return artifact

    def get(self, artifact_id: int) -> GenerationArtifact | None:
        """Return an artifact by id when present."""
        return self._artifacts.get(artifact_id)
