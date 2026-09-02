"""Tests for the in-memory Topic storage adapter."""

from greader.core.topics.models import Topic
from greader.core.topics.repository import InMemoryTopicRepository


def test_repository_returns_saved_topic() -> None:
    repository = InMemoryTopicRepository()
    topic = Topic(id="topic-1", name="Graphs", description="Network problems")

    repository.save(topic)

    assert repository.get("topic-1") == topic


def test_repository_delete_reports_missing_topic() -> None:
    repository = InMemoryTopicRepository()

    assert repository.delete("missing") is False
