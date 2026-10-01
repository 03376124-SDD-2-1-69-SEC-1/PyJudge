"""The in-memory AuthRepository against the shared contract.

`tests/db/test_auth_repository.py` binds the same contract to the SQL adapter.
"""

import pytest

from questly.core.auth.ports import AuthRepository
from tests.contracts.auth_repository import AuthRepositoryContract
from tests.fakes.auth import FakeAuthRepository


class TestFakeAuthRepository(AuthRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> AuthRepository:
        return FakeAuthRepository()
