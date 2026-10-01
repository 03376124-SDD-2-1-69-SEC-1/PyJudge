"""The in-memory DraftRepository against the shared contract.

`tests/db/test_draft_repository.py` binds the same contract to the SQL adapter.
"""

import pytest

from questly.core.generation.ports import DraftRepository
from tests.contracts.draft_repository import DraftRepositoryContract
from tests.fakes.generation import FakeDraftRepository


class TestFakeDraftRepository(DraftRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> DraftRepository:
        return FakeDraftRepository()
