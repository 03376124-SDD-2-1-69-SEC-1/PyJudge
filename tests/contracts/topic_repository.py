"""Contract every TopicRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/topics/` and to
`SQLTopicRepository` in `tests/db/`.
"""

from __future__ import annotations

import pytest

from greader.core.topics.models import Topic
from greader.core.topics.ports import TopicRepository
from greader.core.topics.service import TopicNameConflictError


class TopicRepositoryContract:
    """Checks that hold for any store behind TopicRepository."""

    def test_create_returns_entity_with_non_none_int_id(
        self, repository: TopicRepository
    ) -> None:
        created = repository.create(Topic(name="Graphs", description="Networks"))

        assert isinstance(created.id, int)

    def test_get_after_create_returns_equal_entity(
        self, repository: TopicRepository
    ) -> None:
        created = repository.create(Topic(name="Graphs", description="Networks"))

        assert repository.get(created.id) == created

    def test_get_on_unknown_id_returns_none(self, repository: TopicRepository) -> None:
        assert repository.get(999_999) is None

    def test_find_by_name_ignores_case(self, repository: TopicRepository) -> None:
        created = repository.create(Topic(name="Graphs"))

        assert repository.find_by_name("gRaPhS") == created

    def test_find_by_name_returns_none_when_unused(
        self, repository: TopicRepository
    ) -> None:
        assert repository.find_by_name("Nothing here") is None

    def test_create_rejects_a_name_another_topic_holds(
        self, repository: TopicRepository
    ) -> None:
        repository.create(Topic(name="Graphs"))

        with pytest.raises(TopicNameConflictError):
            repository.create(Topic(name="graphs"))

    def test_update_replaces_stored_values(self, repository: TopicRepository) -> None:
        created = repository.create(Topic(name="Graphs", description="Networks"))

        updated = repository.update(
            Topic(id=created.id, name="Trees", description=None)
        )

        assert updated == Topic(id=created.id, name="Trees", description=None)
        assert repository.get(created.id) == updated

    def test_update_on_unknown_id_raises_key_error(
        self, repository: TopicRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(Topic(id=999_999, name="Ghost"))

    def test_delete_returns_true_once_then_false(
        self, repository: TopicRepository
    ) -> None:
        created = repository.create(Topic(name="Graphs"))

        assert repository.delete(created.id) is True
        assert repository.delete(created.id) is False

    def test_list_returns_every_stored_topic(self, repository: TopicRepository) -> None:
        repository.create(Topic(name="Graphs"))
        repository.create(Topic(name="Trees"))

        assert {topic.name for topic in repository.list()} == {"Graphs", "Trees"}
