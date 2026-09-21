"""The in-memory GenerationRepository against the shared contract.

`tests/db/test_generation_repository.py` binds the same contract to the SQL
adapter, so a behaviour the two do not share fails there.
"""

import pytest

from greader.core.generation.ports import GenerationRepository
from tests.contracts.generation_repository import GenerationRepositoryContract
from tests.fakes.generation import FakeGenerationRepository


class TestFakeGenerationRepository(GenerationRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> GenerationRepository:
        return FakeGenerationRepository()
