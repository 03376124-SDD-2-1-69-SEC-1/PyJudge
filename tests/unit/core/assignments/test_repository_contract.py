"""The in-memory Assignment, Version and Posting repositories against the
shared contracts.

`tests/db/` binds the same contracts to the SQL adapters, so a behaviour the
two do not share fails there.
"""

import pytest

from questly.core.assignments.ports import (
    AssignmentRepository,
    PostingRepository,
    VersionRepository,
)
from tests.contracts.assignment_repository import (
    AssignmentRepositoryContract,
    AssignmentShapeContract,
)
from tests.contracts.posting_repository import PostingRepositoryContract
from tests.contracts.version_repository import VersionRepositoryContract
from tests.fakes.assignments import (
    FakeAssignmentRepository,
    FakePostingRepository,
    FakeVersionRepository,
)


class TestFakeAssignmentRepository(
    AssignmentRepositoryContract, AssignmentShapeContract
):
    """Run the contracts against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> AssignmentRepository:
        return FakeAssignmentRepository()


class TestFakeVersionRepository(VersionRepositoryContract):
    @pytest.fixture()
    def repository(self) -> VersionRepository:
        return FakeVersionRepository()


class TestFakePostingRepository(PostingRepositoryContract):
    @pytest.fixture()
    def repository(self) -> PostingRepository:
        return FakePostingRepository()
