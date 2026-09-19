"""The in-memory TopicRepository against the shared contract.

`tests/db/test_topic_repository.py` binds the same contract to the SQL adapter.
"""

import pytest

from greader.core.topics.ports import TopicRepository
from tests.contracts.topic_repository import TopicRepositoryContract
from tests.fakes.topics import FakeTopicRepository


class TestFakeTopicRepository(TopicRepositoryContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def repository(self) -> TopicRepository:
        return FakeTopicRepository()
