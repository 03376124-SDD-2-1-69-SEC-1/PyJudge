"""The in-memory SubmissionRepository against the shared contract.

`tests/db/test_submission_repository.py` binds the same contract to the SQL
adapter.
"""

import pytest

from questly.core.submissions.ports import SubmissionRepository
from tests.contracts.submission_repository import SubmissionRepositoryContract
from tests.fakes.submissions import FakeSubmissionRepository


class TestFakeSubmissionRepository(SubmissionRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> SubmissionRepository:
        return FakeSubmissionRepository()
