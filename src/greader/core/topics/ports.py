"""Repository port for Topics.

`database/core/topic_repository.py` provides the SQL adapter and
`tests/fakes/topics.py` the in-memory one. Keep TopicService dependent on this
Protocol only.
"""

from typing import Protocol

from greader.core.topics.models import Topic


class TopicRepository(Protocol):
    """Persistence operations required by TopicService.

    `create` is the only operation allowed to assign an id: it takes a Topic
    whose `id` is `None` and returns one whose `id` is a real int. `update` takes
    and returns a Topic that already has its id.
    """

    def list(self) -> list[Topic]:
        """Return every stored Topic."""
        ...

    def get(self, topic_id: int) -> Topic | None:
        """Return one Topic, if it exists."""
        ...

    def find_by_name(self, name: str) -> Topic | None:
        """Return the Topic holding this name, compared case-insensitively."""
        ...

    def create(self, topic: Topic) -> Topic:
        """Insert a Topic and return it with the id the store assigned."""
        ...

    def update(self, topic: Topic) -> Topic:
        """Replace an existing Topic and return the stored value."""
        ...

    def delete(self, topic_id: int) -> bool:
        """Delete a Topic and report whether it existed."""
        ...
