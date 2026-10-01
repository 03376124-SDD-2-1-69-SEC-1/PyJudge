"""ComputedClassroomStats over the in-memory repositories.

`tests/db/test_classroom_stats.py` runs the same contract over the SQL
adapters.
"""

import pytest

from tests.contracts.classroom_stats import ClassroomStatsContract
from tests.fakes.assignments import FakePostingRepository
from tests.fakes.classrooms import FakeClassroomRepository
from tests.fakes.generation import FakeDraftRepository
from tests.fakes.submissions import FakeSubmissionRepository


class TestStatsOverFakes(ClassroomStatsContract):
    @pytest.fixture()
    def postings(self) -> FakePostingRepository:
        return FakePostingRepository()

    @pytest.fixture()
    def submissions(self) -> FakeSubmissionRepository:
        return FakeSubmissionRepository()

    @pytest.fixture()
    def classrooms(self) -> FakeClassroomRepository:
        return FakeClassroomRepository()

    @pytest.fixture()
    def drafts(self) -> FakeDraftRepository:
        return FakeDraftRepository()
