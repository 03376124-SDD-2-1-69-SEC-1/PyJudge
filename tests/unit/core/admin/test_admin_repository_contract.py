import pytest

from tests.contracts.admin_repository import AdminRepositoryContractTests
from tests.fakes.admin import FakeAdminRepository


class TestFakeAdminRepositoryContract(AdminRepositoryContractTests):
    @pytest.fixture
    def repo(self):
        return FakeAdminRepository()