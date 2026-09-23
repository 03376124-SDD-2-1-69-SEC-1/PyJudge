"""Ports the generation slice needs.

ADR-0007 Drafts use DraftRepository, DocumentCatalog, ClassroomLookup and
AssignmentPublisher; production wires the pending adapter for the first two
until OPS-15 and the documents slice, ClassroomService for the lookup, and
AssignmentService as the publisher. GenerationRepository (requests and
artifacts) is the pre-ADR shape: its SQL adapter stays but is not wired.


`ai/client.py` satisfies `GenerationClient`, with a stub today and an HTTP
adapter later (OPS-04). `database/core/generation_repository.py` provides the
SQL adapter for `GenerationRepository` and `tests/fakes/generation.py` the
in-memory one. Nothing in `core/` may import any of them; only `main.py`
wires them in.
"""

from datetime import datetime
from typing import Protocol

from greader.core.assignments.models import (
    AssignmentContent,
    PublishedAssignment,
    Schedule,
)
from greader.core.auth.models import Actor
from greader.core.classrooms.models import Classroom, ClassroomRole
from greader.core.generation.models import (
    AssignmentDraft,
    Citation,
    DocumentSummary,
    Draft,
    GenerationArtifact,
)
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


class DraftRepository(Protocol):
    """Drafts and the log of successful generations the daily Quota counts.

    `create` is the only operation that assigns a Draft its id.
    """

    def create(self, draft: Draft) -> Draft: ...

    def get(self, draft_id: int) -> Draft | None: ...

    def update(self, draft: Draft) -> Draft: ...

    def delete(self, draft_id: int) -> bool: ...

    def list_for_classroom(self, classroom_id: int) -> list[Draft]: ...

    def record_generation(self, user_id: int, at: datetime) -> None: ...

    def count_generations(self, user_id: int, since: datetime) -> int: ...


class DocumentCatalog(Protocol):
    """The Instructor's Document library, owned by the documents slice."""

    def documents_of(self, owner_id: int) -> list[DocumentSummary]: ...


class ClassroomLookup(Protocol):
    """What generation needs from the classrooms slice."""

    def role_of(self, actor: Actor, classroom_id: int) -> ClassroomRole: ...

    def owned_classrooms(self, actor: Actor) -> list[Classroom]: ...

    def member_ids(self, actor: Actor, classroom_id: int) -> list[int]: ...


class AssignmentPublisher(Protocol):
    """T-04 step 4 hands the reviewed content to the assignments slice."""

    def publish(
        self,
        actor: Actor,
        content: AssignmentContent,
        schedule: Schedule,
        classroom_ids: list[int],
        artifact_id: int | None = None,
    ) -> PublishedAssignment: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
