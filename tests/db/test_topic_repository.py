"""SQLTopicRepository against the shared contract, on real Postgres.

Also proves the case-insensitive unique index exists: the conflict rule used to
live only in Python, where two workers could both pass it.
"""

import pytest
from sqlalchemy import text

from greader.core.topics.models import Topic
from greader.core.topics.service import TopicNameConflictError
from greader.database.core.topic_repository import SQLTopicRepository
from greader.database.session import SessionFactory
from tests.contracts.topic_repository import TopicRepositoryContract

pytestmark = pytest.mark.postgres


class TestSQLTopicRepository(TopicRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLTopicRepository:
        return SQLTopicRepository(session_factory)


@pytest.mark.usefixtures("empty_core_tables")
def test_duplicate_name_is_rejected_by_the_database(
    session_factory: SessionFactory,
) -> None:
    repository = SQLTopicRepository(session_factory)
    repository.create(Topic(name="Graphs"))

    # Insert straight through SQL, bypassing the service rule, so what fails is
    # uq_topics_name_lower and not a Python check.
    with session_factory() as session, pytest.raises(Exception):  # noqa: B017
        session.execute(
            text("INSERT INTO core.topics (name) VALUES ('graphs')"),
        )
        session.commit()


@pytest.mark.usefixtures("empty_core_tables")
def test_update_to_a_taken_name_raises_the_domain_error(
    session_factory: SessionFactory,
) -> None:
    repository = SQLTopicRepository(session_factory)
    repository.create(Topic(name="Graphs"))
    trees = repository.create(Topic(name="Trees"))

    with pytest.raises(TopicNameConflictError):
        repository.update(Topic(id=trees.id, name="graphs"))
