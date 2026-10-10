"""`create_app` with nothing injected persists to Postgres (OPS-15).

Built the way production builds it — only settings, R2 and the vector store
swapped out — and pointed at the throwaway branch. The services on `app.state`
then write through whatever `main.py` wired, so rows in the database prove the
SQL adapters are the ones in use. (HTTP-level checks live in
`tests/integration/`, which runs on fakes.)
"""

from dataclasses import replace

import pytest
from sqlalchemy import text

from questly.database.session import SessionFactory
from questly.integrations.email import StubEmailSender
from questly.main import create_app
from tests.fakes.app import fake_settings
from tests.fakes.notifications import FakeNotificationRepository
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
        notification_repository=FakeNotificationRepository(),
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
    auth.verify_email(mailer.sent[-1][1].split("token=", 1)[1])
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
