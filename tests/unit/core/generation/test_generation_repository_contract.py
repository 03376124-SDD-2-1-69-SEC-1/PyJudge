"""The in-memory GenerationRepository against the shared contract.

The pre-ADR port has no SQL adapter since OPS-15 (ADR-0008): Drafts replaced
it. Only the fake is held to the contract until the port itself is retired.
"""

import pytest

from questly.core.generation.ports import GenerationRepository
from tests.contracts.generation_repository import GenerationRepositoryContract
from tests.fakes.generation import FakeGenerationRepository


class TestFakeGenerationRepository(GenerationRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> GenerationRepository:
        return FakeGenerationRepository()
