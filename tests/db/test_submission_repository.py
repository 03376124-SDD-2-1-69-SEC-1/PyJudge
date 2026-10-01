"""SQLSubmissionRepository against the shared contract, on real Postgres."""

import pytest

from questly.database.core.posting_repository import SQLPostingRepository
from questly.database.core.submission_repository import SQLSubmissionRepository
from questly.database.session import SessionFactory
from tests.contracts.submission_repository import (
    SubmissionRepositoryContract,
    submission,
)
from tests.contracts.support import IdFactory, PostingFactory
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestSQLSubmissionRepository(RealRows, SubmissionRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLSubmissionRepository:
        return SQLSubmissionRepository(session_factory)

    def test_unposting_deletes_the_postings_submissions(
        self,
        repository: SQLSubmissionRepository,
        session_factory: SessionFactory,
        new_posting: PostingFactory,
        new_user: IdFactory,
    ) -> None:
        """ADR-0008: submissions.posting_id is ON DELETE CASCADE."""
        where = new_posting()
        added = repository.add(submission(where, new_user()))

        assert SQLPostingRepository(session_factory).delete(where.posting_id)
        assert repository.get(added.id) is None
