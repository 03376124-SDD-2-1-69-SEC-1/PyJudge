"""The in-memory ClassroomRepository against the shared contract.

`tests/db/test_classroom_repository.py` binds the same contract to the SQL
adapter.
"""

import pytest

from questly.core.classrooms.ports import ClassroomRepository
from tests.contracts.classroom_repository import ClassroomRepositoryContract
from tests.fakes.classrooms import FakeClassroomRepository


class TestFakeClassroomRepository(ClassroomRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> ClassroomRepository:
        return FakeClassroomRepository()
