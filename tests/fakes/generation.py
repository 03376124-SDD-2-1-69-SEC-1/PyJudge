"""In-memory GenerationRepository, behaviour-matched to the SQL adapter."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from greader.core.generation.models import (
    AssignmentDraft,
    Citation,
    DocumentSummary,
    Draft,
    GenerationArtifact,
)
from greader.core.generation.schemas import GenerationRequest, GenerationResponse
from greader.database.core.generation_repository import (
    citation_from_json,
    citation_to_json,
    draft_from_json,
    draft_to_json,
)


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
        """Insert an artifact linked to `request_id` and return it with an id.

        Round-trips `draft`/`citations` through the same JSON codec the SQL
        adapter uses, so a contract test run against this fake exercises the
        codec instead of just handing the same object back by reference.
        """
        artifact_id = self._next_artifact_id
        self._next_artifact_id += 1
        artifact = GenerationArtifact(
            id=artifact_id,
            draft=draft_from_json(draft_to_json(draft)),
            citations=[
                citation_from_json(citation_to_json(citation)) for citation in citations
            ],
        )
        self._artifacts[artifact_id] = artifact
        return artifact

    def get(self, artifact_id: int) -> GenerationArtifact | None:
        """Return an artifact by id when present."""
        return self._artifacts.get(artifact_id)


class FakeDraftRepository:
    """Drafts and the generation log in process."""

    def __init__(self) -> None:
        self._items: dict[int, Draft] = {}
        self._next_id = 1
        self.generations: list[tuple[int, datetime]] = []

    def create(self, draft: Draft) -> Draft:
        created = replace(draft, id=self._next_id)
        self._next_id += 1
        self._items[created.id] = created
        return created

    def get(self, draft_id: int) -> Draft | None:
        return self._items.get(draft_id)

    def update(self, draft: Draft) -> Draft:
        self._items[draft.id]  # KeyError for an unknown id
        self._items[draft.id] = draft
        return draft

    def delete(self, draft_id: int) -> bool:
        return self._items.pop(draft_id, None) is not None

    def list_for_classroom(self, classroom_id: int) -> list[Draft]:
        return [
            self._items[key]
            for key in sorted(self._items)
            if self._items[key].classroom_id == classroom_id
        ]

    def record_generation(self, user_id: int, at: datetime) -> None:
        self.generations.append((user_id, at))

    def count_generations(self, user_id: int, since: datetime) -> int:
        return sum(1 for who, at in self.generations if who == user_id and at >= since)


class FakeDocumentCatalog:
    """Documents per owner, set by a test or the demo seed."""

    def __init__(self) -> None:
        self.by_owner: dict[int, list[DocumentSummary]] = {}

    def documents_of(self, owner_id: int) -> list[DocumentSummary]:
        if owner_id in self.by_owner:
            return list(self.by_owner[owner_id])
        return []


class FakeGenerationClient:
    """Returns `response`, or raises when `fail` is set (T-03d)."""

    def __init__(self, response: GenerationResponse) -> None:
        self.response = response
        self.fail = False
        self.requests: list[GenerationRequest] = []

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        if self.fail:
            raise TimeoutError("the model did not respond")
        return self.response


def binary_search_response() -> GenerationResponse:
    """The T-03a draft from the prototype, as a GenerationClient would return it."""
    return GenerationResponse.model_validate(
        {
            "draft": {
                "title": "Binary search on sorted input",
                "statement": (
                    "Read an integer n, a sorted list of n integers and a target "
                    "value x. Print the index of x using binary search, or -1 if "
                    "x is not present. Indices start at 0."
                ),
                "test_cases": [
                    {"input_data": "5\n1 3 5 7 9\n7", "expected_output": "3"},
                    {"input_data": "4\n2 4 6 8\n5", "expected_output": "-1"},
                    {
                        "input_data": "1\n4\n4",
                        "expected_output": "0",
                        "is_hidden": True,
                    },
                ],
            },
            "citations": [
                {
                    "chunk_id": 1,
                    "source_id": 1,
                    "page": 9,
                    "score": 0.92,
                    "text_snapshot": "Binary search halves the interval each step.",
                }
            ],
        }
    )
