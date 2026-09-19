"""The in-memory AssignmentRepository against the shared contract.

`tests/db/test_assignment_repository.py` binds the same contract to the SQL
adapter, so a behaviour the two do not share fails there.
"""

import pytest

from greader.core.assignments.ports import AssignmentRepository
from tests.contracts.assignment_repository import AssignmentRepositoryContract
from tests.fakes.assignments import FakeAssignmentRepository


class TestFakeAssignmentRepository(AssignmentRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> AssignmentRepository:
        return FakeAssignmentRepository()
