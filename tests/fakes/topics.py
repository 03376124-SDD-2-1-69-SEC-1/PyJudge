"""In-memory TopicRepository, behaviour-matched to the SQL adapter."""

from __future__ import annotations

from dataclasses import replace

from greader.core.topics.models import Topic
from greader.core.topics.service import TopicNameConflictError


class FakeTopicRepository:
    """Store Topics in process for tests and local experiments."""

    def __init__(self) -> None:
        """Initialize an empty repository."""
        self._items: dict[int, Topic] = {}
        self._next_id = 1

    def list(self) -> list[Topic]:
        """Return every stored Topic, oldest first."""
        return [self._items[key] for key in sorted(self._items)]

    def get(self, topic_id: int) -> Topic | None:
        """Return one Topic, if it exists."""
        return self._items.get(topic_id)

    def find_by_name(self, name: str) -> Topic | None:
        """Return the Topic holding this name, compared case-insensitively."""
        folded = name.casefold()
        for topic in self._items.values():
            if topic.name.casefold() == folded:
                return topic
        return None

    def create(self, topic: Topic) -> Topic:
        """Insert a Topic and return it with a generated id.

        Raises TopicNameConflictError on a duplicate name, which is what the SQL
        adapter reports when `uq_topics_name_lower` rejects the insert.
        """
        self._reject_duplicate_name(topic.name, excluding_topic_id=None)
        new_id = self._next_id
        self._next_id += 1
        created = replace(topic, id=new_id)
        self._items[new_id] = created
        return created

    def update(self, topic: Topic) -> Topic:
        """Replace an existing Topic and return the stored value.

        Raises KeyError for an unknown id, like the SQL adapter.
        """
        existing = self._items[topic.id]
        self._reject_duplicate_name(topic.name, excluding_topic_id=existing.id)
        updated = replace(topic, id=existing.id)
        self._items[existing.id] = updated
        return updated

    def delete(self, topic_id: int) -> bool:
        """Delete a Topic and report whether it existed."""
        return self._items.pop(topic_id, None) is not None

    def _reject_duplicate_name(
        self, name: str, *, excluding_topic_id: int | None
    ) -> None:
        owner = self.find_by_name(name)
        if owner is None:
            return
        if excluding_topic_id is not None and owner.id == excluding_topic_id:
            return
        raise TopicNameConflictError
