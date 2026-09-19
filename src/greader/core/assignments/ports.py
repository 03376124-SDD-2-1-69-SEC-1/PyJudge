"""Repository port for Assignments.

`database/core/assignment_repository.py` provides the SQL adapter and
`tests/fakes/assignments.py` the in-memory one. Both satisfy this Protocol;
neither may be imported from `core/`.
"""

from __future__ import annotations

from typing import Protocol

from greader.core.assignments.models import Assignment


class AssignmentRepository(Protocol):
    """Persistence operations required by AssignmentService.

    `create` and `update` are the only operations allowed to assign an id, and
    they do it for the aggregate root and its test cases alike: an Assignment or
    TestCase whose `id` is `None` comes back with a real int. Every other
    operation takes and returns objects that already have their ids. Callers must
    always use the returned object, never the one they passed in.
    """

    def list(self) -> list[Assignment]: ...

    def get(self, assignment_id: int) -> Assignment | None: ...

    def create(self, assignment: Assignment) -> Assignment: ...

    def update(self, assignment: Assignment) -> Assignment: ...

    def delete(self, assignment_id: int) -> bool: ...
