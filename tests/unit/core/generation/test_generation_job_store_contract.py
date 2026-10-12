import pytest

from questly.integrations.generation_jobs import InMemoryGenerationJobStore
from tests.contracts.generation_job_store import GenerationJobStoreContractTests
from tests.fakes.generation import FakeGenerationJobStore


class TestFakeGenerationJobStore(GenerationJobStoreContractTests):
    @pytest.fixture()
    def make_store(self) -> type[FakeGenerationJobStore]:
        return FakeGenerationJobStore

    @pytest.fixture()
    def store(self, make_store: type[FakeGenerationJobStore]) -> FakeGenerationJobStore:
        return make_store()


class TestInMemoryGenerationJobStore(GenerationJobStoreContractTests):
    @pytest.fixture()
    def make_store(self) -> type[InMemoryGenerationJobStore]:
        return InMemoryGenerationJobStore

    @pytest.fixture()
    def store(
        self, make_store: type[InMemoryGenerationJobStore]
    ) -> InMemoryGenerationJobStore:
        return make_store()
