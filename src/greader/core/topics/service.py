"""Topic use cases independent from HTTP and database technology."""

from uuid import uuid4

from greader.core.topics.models import Topic
from greader.core.topics.repository import TopicRepository


class TopicNameConflictError(Exception):
    """Raised when a normalized Topic name is already in use."""


class TopicNotFoundError(Exception):
    """Raised when a requested Topic does not exist."""


class _Unset:
    """Marks a PATCH field left out of the request body."""


UNSET = _Unset()


class TopicService:
    """Coordinates Topic rules through a repository seam."""

    def __init__(self, repository: TopicRepository) -> None:
        self._repository = repository

    def create(self, *, name: str, description: str | None) -> Topic:
        name, description = _normalize_values(name, description)
        self._ensure_name_available(name)
        topic = Topic(id=str(uuid4()), name=name, description=description)
        self._repository.save(topic)
        return topic

    def list(self) -> list[Topic]:
        return sorted(self._repository.list(), key=lambda topic: topic.name.casefold())

    def get(self, topic_id: str) -> Topic:
        topic = self._repository.get(topic_id)
        if topic is None:
            raise TopicNotFoundError
        return topic

    def replace(
        self,
        *,
        topic_id: str,
        name: str,
        description: str | None,
    ) -> Topic:
        self.get(topic_id)
        name, description = _normalize_values(name, description)
        self._ensure_name_available(name, excluding_topic_id=topic_id)
        topic = Topic(id=topic_id, name=name, description=description)
        self._repository.save(topic)
        return topic

    def patch(
        self,
        *,
        topic_id: str,
        name: str | _Unset = UNSET,
        description: str | None | _Unset = UNSET,
    ) -> Topic:
        current = self.get(topic_id)
        new_name = current.name if name is UNSET else name
        new_description = current.description if description is UNSET else description
        new_name, new_description = _normalize_values(new_name, new_description)
        self._ensure_name_available(new_name, excluding_topic_id=topic_id)
        topic = Topic(id=topic_id, name=new_name, description=new_description)
        self._repository.save(topic)
        return topic

    def delete(self, topic_id: str) -> None:
        if not self._repository.delete(topic_id):
            raise TopicNotFoundError

    def _ensure_name_available(
        self,
        name: str,
        *,
        excluding_topic_id: str | None = None,
    ) -> None:
        normalized_name = name.casefold()
        for topic in self._repository.list():
            is_duplicate = (
                topic.id != excluding_topic_id
                and topic.name.casefold() == normalized_name
            )
            if is_duplicate:
                raise TopicNameConflictError


def _normalize_values(name: str, description: str | None) -> tuple[str, str | None]:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be blank")
    normalized_description = description.strip() if description else None
    return normalized_name, normalized_description or None
