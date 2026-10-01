"""SQLClassroomRepository against the shared contract, on real Postgres."""

import pytest
from sqlalchemy.exc import IntegrityError

from questly.core.classrooms.models import Membership
from questly.database.core.classroom_repository import SQLClassroomRepository
from questly.database.session import SessionFactory
from tests.contracts.classroom_repository import (
    NOW,
    ClassroomRepositoryContract,
    classroom,
)
from tests.contracts.support import IdFactory
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestSQLClassroomRepository(RealRows, ClassroomRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLClassroomRepository:
        return SQLClassroomRepository(session_factory)


class TestDatabaseConstraints(RealRows):
    """Rules the service checks first, held again by the schema."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLClassroomRepository:
        return SQLClassroomRepository(session_factory)

    def test_a_student_joins_a_classroom_once(
        self, repository: SQLClassroomRepository, new_user: IdFactory
    ) -> None:
        room = repository.create(classroom(new_user()))
        student = new_user()
        repository.add_membership(Membership(room.id, student, NOW))

        with pytest.raises(IntegrityError):
            repository.add_membership(Membership(room.id, student, NOW))

    def test_join_codes_are_unique(
        self, repository: SQLClassroomRepository, new_user: IdFactory
    ) -> None:
        repository.create(classroom(new_user(), join_code="SAME01"))

        with pytest.raises(IntegrityError):
            repository.create(classroom(new_user(), join_code="SAME01"))
