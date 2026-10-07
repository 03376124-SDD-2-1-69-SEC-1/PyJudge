"""ComputedClassroomStats over the SQL adapters, on real Postgres."""

import pytest

from questly.database.core.classroom_repository import SQLClassroomRepository
from questly.database.core.draft_repository import SQLDraftRepository
from questly.database.core.posting_repository import SQLPostingRepository
from questly.database.core.submission_repository import SQLSubmissionRepository
from questly.database.session import SessionFactory
from tests.contracts.classroom_stats import ClassroomStatsContract
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestStatsOverSQL(RealRows, ClassroomStatsContract):
    @pytest.fixture()
    def postings(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLPostingRepository:
        return SQLPostingRepository(session_factory)

    @pytest.fixture()
    def submissions(self, session_factory: SessionFactory) -> SQLSubmissionRepository:
        return SQLSubmissionRepository(session_factory)

    @pytest.fixture()
    def classrooms(self, session_factory: SessionFactory) -> SQLClassroomRepository:
        return SQLClassroomRepository(session_factory)

    @pytest.fixture()
    def drafts(self, session_factory: SessionFactory) -> SQLDraftRepository:
        return SQLDraftRepository(session_factory)
