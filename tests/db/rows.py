"""Row factories for SQL contract bindings.

`RealRows` overrides the id factories in `tests/contracts/support.py` with ones
that insert real rows, so foreign keys hold. Mix it in *before* the contract.
"""

from datetime import UTC, datetime
from itertools import count

import pytest

from questly.database.core.tables import Assignment as AssignmentRow
from questly.database.core.tables import Classroom as ClassroomRow
from questly.database.core.tables import Posting as PostingRow
from questly.database.core.tables import Topic as TopicRow
from questly.database.core.tables import User as UserRow
from questly.database.session import SessionFactory
from tests.contracts.support import IdFactory, PostingFactory, PostingIds


class RealRows:
    """Real-row factories; their fixtures win over the contract defaults."""

    @pytest.fixture()
    def new_user(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> IdFactory:
        ids = count(1)

        def create() -> int:
            with session_factory() as session:
                row = UserRow(
                    email=f"user{next(ids)}@kmitl.ac.th",
                    full_name="Test User",
                    password_hash="scrypt$x",
                    role="instructor",
                )
                session.add(row)
                session.commit()
                return row.id

        return create

    @pytest.fixture()
    def new_classroom(
        self, session_factory: SessionFactory, new_user: IdFactory
    ) -> IdFactory:
        def create() -> int:
            with session_factory() as session:
                row = ClassroomRow(
                    instructor_id=new_user(),
                    course_code="01076001",
                    course_name="Programming",
                    section="1",
                    semester="1/2569",
                )
                session.add(row)
                session.commit()
                return row.id

        return create

    @pytest.fixture()
    def new_assignment(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> IdFactory:
        def create() -> int:
            with session_factory() as session:
                row = AssignmentRow(
                    title="Binary search",
                    problem_statement="Find x.",
                    difficulty="easy",
                )
                session.add(row)
                session.commit()
                return row.id

        return create

    @pytest.fixture()
    def new_topic(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> IdFactory:
        ids = count(1)

        def create() -> int:
            with session_factory() as session:
                row = TopicRow(name=f"Topic {next(ids)}")
                session.add(row)
                session.commit()
                return row.id

        return create

    @pytest.fixture()
    def new_posting(
        self,
        session_factory: SessionFactory,
        new_classroom: IdFactory,
        new_assignment: IdFactory,
    ) -> PostingFactory:
        def create() -> PostingIds:
            classroom_id, assignment_id = new_classroom(), new_assignment()
            moment = datetime(2026, 9, 28, 9, 0, tzinfo=UTC)
            with session_factory() as session:
                row = PostingRow(
                    classroom_id=classroom_id,
                    assignment_id=assignment_id,
                    deadline=moment,
                    max_score=10,
                    allow_late=False,
                    allow_resubmission=True,
                    published_at=moment,
                )
                session.add(row)
                session.commit()
                return PostingIds(row.id, classroom_id, assignment_id)

        return create
