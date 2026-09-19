"""SQL adapter for the TopicRepository port (OPS-12)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from greader.core.topics.models import Topic
from greader.core.topics.service import TopicNameConflictError
from greader.database.core.tables import Topic as TopicRow
from greader.database.session import SessionFactory


def _to_domain(row: TopicRow) -> Topic:
    return Topic(id=row.id, name=row.name, description=row.description)


class SQLTopicRepository:
    """Store Topics in the `core` schema.

    One session per method, like every other adapter here: the service is built
    once at startup, so each call is its own unit of work.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def list(self) -> list[Topic]:
        """Return every stored Topic."""
        with self._session_factory() as session:
            rows = session.exec(select(TopicRow).order_by(TopicRow.id)).all()
            return [_to_domain(row) for row in rows]

    def get(self, topic_id: int) -> Topic | None:
        """Return one Topic, if it exists."""
        with self._session_factory() as session:
            row = session.get(TopicRow, topic_id)
            if row is None:
                return None
            return _to_domain(row)

    def find_by_name(self, name: str) -> Topic | None:
        """Return the Topic holding this name, compared case-insensitively.

        Uses the same `lower(name)` expression as `uq_topics_name_lower`, so the
        lookup reads the index the constraint already maintains.
        """
        with self._session_factory() as session:
            row = session.exec(
                select(TopicRow).where(func.lower(TopicRow.name) == name.lower())
            ).first()
            if row is None:
                return None
            return _to_domain(row)

    def create(self, topic: Topic) -> Topic:
        """Insert a Topic and return it with the id the database assigned."""
        with self._session_factory() as session:
            row = TopicRow(name=topic.name, description=topic.description)
            session.add(row)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise TopicNameConflictError from error
            session.refresh(row)
            return _to_domain(row)

    def update(self, topic: Topic) -> Topic:
        """Replace an existing Topic and return the stored value.

        Raises KeyError when the id does not exist, matching the in-memory
        adapter: the Protocol says `update` takes a Topic that already has its
        id, so a missing row is a programming error, not a 404.
        """
        with self._session_factory() as session:
            row = session.get(TopicRow, topic.id)
            if row is None:
                raise KeyError(topic.id)
            row.name = topic.name
            row.description = topic.description
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise TopicNameConflictError from error
            session.refresh(row)
            return _to_domain(row)

    def delete(self, topic_id: int) -> bool:
        """Delete a Topic and report whether it existed."""
        with self._session_factory() as session:
            row = session.get(TopicRow, topic_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
