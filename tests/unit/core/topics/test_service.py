"""Tests for Topic application rules."""

import pytest

from greader.core.topics.repository import InMemoryTopicRepository
from greader.core.topics.service import TopicNameConflictError, TopicService


def test_create_normalizes_topic_values() -> None:
    service = TopicService(InMemoryTopicRepository())

    topic = service.create(name="  Graphs ", description="  Network problems  ")

    assert topic.name == "Graphs"
    assert topic.description == "Network problems"


def test_create_rejects_case_insensitive_duplicate_name() -> None:
    service = TopicService(InMemoryTopicRepository())
    service.create(name="Graphs", description=None)

    with pytest.raises(TopicNameConflictError):
        service.create(name="graphs", description=None)


def test_list_is_ordered_by_normalized_name() -> None:
    service = TopicService(InMemoryTopicRepository())
    service.create(name="Trees", description=None)
    service.create(name="arrays", description=None)

    assert [topic.name for topic in service.list()] == ["arrays", "Trees"]
