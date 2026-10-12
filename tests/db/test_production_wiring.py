"""`create_app` with nothing injected persists to Postgres (OPS-15).

Built the way production builds it — only settings, R2 and the vector store
swapped out — and pointed at the throwaway branch. The services on `app.state`
then write through whatever `main.py` wired, so rows in the database prove the
SQL adapters are the ones in use. (HTTP-level checks live in
`tests/integration/`, which runs on fakes.)
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from questly.core.assignments.models import (
    AssignmentContent,
    Difficulty,
    Schedule,
    TestCase,
)
from questly.core.auth.models import Actor, Role
from questly.database.core.tables import User as UserRow
from questly.database.session import SessionFactory
from questly.integrations.email import StubEmailSender
from questly.main import create_app
from tests.fakes.app import fake_settings
from tests.fakes.auth import verification_path
from tests.fakes.uploads import FakeObjectStorage
from tests.fakes.vector import FakeVectorRepository

pytestmark = pytest.mark.postgres


@pytest.mark.usefixtures("empty_core_tables")
def test_sign_up_verify_and_log_in_write_to_postgres(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    mailer = StubEmailSender()
    app = create_app(
        settings=replace(fake_settings(), database_url=postgres_url),
        email_sender=mailer,
        object_storage=FakeObjectStorage(),
        vector_repository=FakeVectorRepository(),
    )
    auth = app.state.auth_service

    auth.sign_up(
        full_name="Somchai Prasert",
        email="somchai@kmitl.ac.th",
        password="correct horse",
        confirm_password="correct horse",
        wants_instructor=True,
        faculty="Engineering",
    )
    auth.verify_email(verification_path(mailer).split("token=", 1)[1])
    login = auth.log_in(email="somchai@kmitl.ac.th", password="correct horse")

    assert auth.resolve_session(login.token).full_name == "Somchai Prasert"
    with session_factory() as session:
        stored = session.execute(
            text(
                "SELECT u.full_name, u.email_verified_at IS NOT NULL, "
                "(SELECT count(*) FROM core.sessions s WHERE s.user_id = u.id), "
                "(SELECT faculty FROM core.instructor_requests r "
                " WHERE r.user_id = u.id) "
                "FROM core.users u"
            )
        ).one()
    assert tuple(stored) == ("Somchai Prasert", True, 1, "Engineering")


def _account(session_factory: SessionFactory, email: str, role: Role) -> Actor:
    with session_factory() as session:
        row = UserRow(
            email=email,
            full_name=email,
            password_hash="scrypt$x",
            role=role.value,
            email_verified_at=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        return Actor(user_id=row.id, role=role, full_name=email, email=email)


@pytest.mark.usefixtures("empty_core_tables")
def test_publishing_stores_a_notification_per_member_in_postgres(
    postgres_url: str, session_factory: SessionFactory
) -> None:
    mailer = StubEmailSender()
    app = create_app(
        settings=replace(fake_settings(), database_url=postgres_url),
        email_sender=mailer,
        object_storage=FakeObjectStorage(),
        vector_repository=FakeVectorRepository(),
    )
    teacher = _account(session_factory, "somchai.p@kmitl.ac.th", Role.INSTRUCTOR)
    student = _account(session_factory, "66010001@kmitl.ac.th", Role.STUDENT)
    classrooms = app.state.classroom_service
    classroom = classrooms.create(
        teacher,
        course_code="01076001",
        course_name="Programming I",
        section="1",
        semester="1/2569",
    )
    classrooms.join(student, classroom.join_code)

    published = app.state.assignment_service.publish(
        teacher,
        AssignmentContent(
            title="Binary search",
            problem_statement="Print the index of x, or -1.",
            difficulty=Difficulty.MEDIUM,
            test_cases=[TestCase(input_data="1\n4\n4", expected_output="0")],
        ),
        Schedule(deadline=datetime.now(UTC) + timedelta(days=7)),
        [classroom.id],
    )

    with session_factory() as session:
        stored = session.execute(
            text("SELECT user_id, kind, payload, read_at FROM core.notifications")
        ).all()
    assert [tuple(row) for row in stored] == [
        (
            student.user_id,
            "assignment_published",
            {
                "classroom_id": classroom.id,
                "assignment_id": published.assignment.id,
                "title": "Binary search",
            },
            None,
        )
    ]
    assert [m.to for m in mailer.messages] == [student.email]
