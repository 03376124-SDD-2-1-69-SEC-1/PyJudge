"""Tests for Topic application rules."""

import pytest

from greader.core.topics.service import (
    TopicNameConflictError,
    TopicNotFoundError,
    TopicService,
)
from tests.fakes.topics import FakeTopicRepository


def test_create_normalizes_topic_values() -> None:
    service = TopicService(FakeTopicRepository())

    topic = service.create(name="  Graphs ", description="  Network problems  ")

    assert topic.name == "Graphs"
    assert topic.description == "Network problems"


def test_create_assigns_an_int_id() -> None:
    service = TopicService(FakeTopicRepository())

    topic = service.create(name="Graphs", description=None)

    assert isinstance(topic.id, int)


def test_create_rejects_case_insensitive_duplicate_name() -> None:
    service = TopicService(FakeTopicRepository())
    service.create(name="Graphs", description=None)

    with pytest.raises(TopicNameConflictError):
        service.create(name="graphs", description=None)


def test_list_is_ordered_by_normalized_name() -> None:
    service = TopicService(FakeTopicRepository())
    service.create(name="Trees", description=None)
    service.create(name="arrays", description=None)

    assert [topic.name for topic in service.list()] == ["arrays", "Trees"]


def test_replace_overwrites_the_description() -> None:
    service = TopicService(FakeTopicRepository())
    topic = service.create(name="Graphs", description="Network problems")

    replaced = service.replace(topic_id=topic.id, name="Graphs", description=None)

    assert replaced.description is None


def test_patch_updates_only_the_given_field() -> None:
    service = TopicService(FakeTopicRepository())
    topic = service.create(name="Graphs", description="Network problems")

    patched = service.patch(topic_id=topic.id, name="Trees")

    assert patched.name == "Trees"
    assert patched.description == "Network problems"


def test_patch_with_no_fields_is_a_no_op() -> None:
    service = TopicService(FakeTopicRepository())
    topic = service.create(name="Graphs", description="Network problems")

    patched = service.patch(topic_id=topic.id)

    assert patched.name == "Graphs"
    assert patched.description == "Network problems"


def test_patch_unknown_topic_raises_not_found() -> None:
    service = TopicService(FakeTopicRepository())

    with pytest.raises(TopicNotFoundError):
        service.patch(topic_id=999, name="Trees")


def test_patch_rejects_case_insensitive_duplicate_name() -> None:
    service = TopicService(FakeTopicRepository())
    service.create(name="Graphs", description=None)
    topic = service.create(name="Trees", description=None)

    with pytest.raises(TopicNameConflictError):
        service.patch(topic_id=topic.id, name="graphs")


def test_delete_unknown_topic_raises_not_found() -> None:
    service = TopicService(FakeTopicRepository())

    with pytest.raises(TopicNotFoundError):
        service.delete(999)
