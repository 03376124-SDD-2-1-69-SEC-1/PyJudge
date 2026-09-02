"""Storage seam and in-memory adapter for Topics.

When the database owner defines the Core schema, add a new adapter here or in
the database package. Keep TopicService dependent on TopicRepository.
"""

from typing import Protocol

from greader.core.topics.models import Topic


class TopicRepository(Protocol):
    """Database operations required by Topic use cases."""

    def list(self) -> list[Topic]:
        """Return every stored Topic."""
        ...

    def get(self, topic_id: str) -> Topic | None:
        """Return one Topic, if it exists."""
        ...

    def save(self, topic: Topic) -> None:
        """Create or replace a Topic."""
        ...

    def delete(self, topic_id: str) -> bool:
        """Delete a Topic and report whether it existed."""
        ...


class InMemoryTopicRepository:
    """Process-local storage used until a database adapter exists."""

    def __init__(self) -> None:
        self._topics: dict[str, Topic] = {}

    def list(self) -> list[Topic]:
        return list(self._topics.values())

    def get(self, topic_id: str) -> Topic | None:
        return self._topics.get(topic_id)

    def save(self, topic: Topic) -> None:
        self._topics[topic.id] = topic

    def delete(self, topic_id: str) -> bool:
        return self._topics.pop(topic_id, None) is not None
