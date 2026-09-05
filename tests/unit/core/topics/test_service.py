"""Tests for Topic application rules."""

import pytest

from greader.core.topics.repository import InMemoryTopicRepository
from greader.core.topics.service import (
    TopicNameConflictError,
    TopicNotFoundError,
    TopicService,
)


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


def test_patch_updates_only_the_given_field() -> None:
    service = TopicService(InMemoryTopicRepository())
    topic = service.create(name="Graphs", description="Network problems")

    patched = service.patch(topic_id=topic.id, name="Trees")

    assert patched.name == "Trees"
    assert patched.description == "Network problems"


def test_patch_with_no_fields_is_a_no_op() -> None:
    service = TopicService(InMemoryTopicRepository())
    topic = service.create(name="Graphs", description="Network problems")

    patched = service.patch(topic_id=topic.id)

    assert patched.name == "Graphs"
    assert patched.description == "Network problems"


def test_patch_unknown_topic_raises_not_found() -> None:
    service = TopicService(InMemoryTopicRepository())

    with pytest.raises(TopicNotFoundError):
        service.patch(topic_id="missing", name="Trees")


def test_patch_rejects_case_insensitive_duplicate_name() -> None:
    service = TopicService(InMemoryTopicRepository())
    service.create(name="Graphs", description=None)
    topic = service.create(name="Trees", description=None)

    with pytest.raises(TopicNameConflictError):
        service.patch(topic_id=topic.id, name="graphs")
