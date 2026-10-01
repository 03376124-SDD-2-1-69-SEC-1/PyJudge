"""SQL adapter for the AuthRepository port (OPS-15)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, update
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import select

from questly.core.auth.models import (
    InstructorRequest,
    InstructorRequestStatus,
    Role,
    Session,
    User,
    VerificationToken,
)
from questly.database.core.tables import EmailVerificationToken as TokenRow
from questly.database.core.tables import InstructorRequestRow
from questly.database.core.tables import User as UserRow
from questly.database.core.tables import UserSession as SessionRow
from questly.database.session import SessionFactory


def _stamp(flag: bool, current: datetime | None) -> datetime | ColumnElement | None:
    """Map a domain flag onto its timestamp column (ADR-0008).

    Keep the stored moment while the flag stays on, stamp `now()` when it turns
    on, and clear it when it turns off.
    """
    if not flag:
        return None
    if current is None:
        return func.now()
    return current


def _user(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        password_hash=row.password_hash,
        role=Role(row.role),
        email_verified=row.email_verified_at is not None,
        is_active=row.is_active,
        last_active_at=row.last_active_at,
    )


def _session(row: SessionRow) -> Session:
    return Session(
        id=row.id,
        token_hash=row.token_hash,
        user_id=row.user_id,
        expires_at=row.expires_at,
        csrf_token=row.csrf_token,
        revoked=row.revoked_at is not None,
    )


def _token(row: TokenRow) -> VerificationToken:
    return VerificationToken(
        id=row.id,
        token_hash=row.token_hash,
        user_id=row.user_id,
        expires_at=row.expires_at,
        used=row.used_at is not None,
    )


def _request(row: InstructorRequestRow) -> InstructorRequest:
    return InstructorRequest(
        id=row.id,
        user_id=row.user_id,
        faculty=row.faculty,
        requested_at=row.requested_at,
        status=InstructorRequestStatus(row.status),
    )


class SQLAuthRepository:
    """Store accounts, Sessions, verification tokens and Instructor requests.

    One session per method, like every adapter here. An update on an unknown id
    raises KeyError: the port only updates entities it was handed back.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    # ---- users -------------------------------------------------------------

    def get_user(self, user_id: int) -> User | None:
        """Return one account, if it exists."""
        with self._session_factory() as db:
            row = db.get(UserRow, user_id)
            if row is None:
                return None
            return _user(row)

    def find_user_by_email(self, email: str) -> User | None:
        """Return the account with exactly this email, if any."""
        with self._session_factory() as db:
            row = db.exec(select(UserRow).where(UserRow.email == email)).first()
            if row is None:
                return None
            return _user(row)

    def list_users(self) -> list[User]:
        """Return every account in id order."""
        with self._session_factory() as db:
            rows = db.exec(select(UserRow).order_by(UserRow.id)).all()
            return [_user(row) for row in rows]

    def create_user(self, user: User) -> User:
        """Insert an account and return it with its new id."""
        with self._session_factory() as db:
            row = UserRow(
                email=user.email,
                full_name=user.full_name,
                password_hash=user.password_hash,
                role=user.role.value,
                email_verified_at=_stamp(user.email_verified, None),
                is_active=user.is_active,
                last_active_at=user.last_active_at,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _user(row)

    def update_user(self, user: User) -> User:
        """Replace an existing account and return the stored value."""
        with self._session_factory() as db:
            row = db.get(UserRow, user.id)
            if row is None:
                raise KeyError(user.id)
            row.email = user.email
            row.full_name = user.full_name
            row.password_hash = user.password_hash
            row.role = user.role.value
            row.email_verified_at = _stamp(user.email_verified, row.email_verified_at)
            row.is_active = user.is_active
            row.last_active_at = user.last_active_at
            db.commit()
            db.refresh(row)
            return _user(row)

    # ---- sessions ----------------------------------------------------------

    def create_session(self, session: Session) -> Session:
        """Insert a login Session and return it with its new id."""
        with self._session_factory() as db:
            row = SessionRow(
                user_id=session.user_id,
                token_hash=session.token_hash,
                csrf_token=session.csrf_token,
                expires_at=session.expires_at,
                revoked_at=_stamp(session.revoked, None),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _session(row)

    def find_session(self, token_hash: str) -> Session | None:
        """Return the Session whose cookie hashes to this value, if any."""
        with self._session_factory() as db:
            row = db.exec(
                select(SessionRow).where(SessionRow.token_hash == token_hash)
            ).first()
            if row is None:
                return None
            return _session(row)

    def update_session(self, session: Session) -> Session:
        """Replace an existing Session and return the stored value."""
        with self._session_factory() as db:
            row = db.get(SessionRow, session.id)
            if row is None:
                raise KeyError(session.id)
            row.expires_at = session.expires_at
            row.csrf_token = session.csrf_token
            row.revoked_at = _stamp(session.revoked, row.revoked_at)
            db.commit()
            db.refresh(row)
            return _session(row)

    def revoke_sessions_of(self, user_id: int) -> None:
        """Revoke every Session of one account that is still live."""
        with self._session_factory() as db:
            db.exec(
                update(SessionRow)
                .where(SessionRow.user_id == user_id, SessionRow.revoked_at.is_(None))
                .values(revoked_at=func.now())
            )
            db.commit()

    # ---- verification tokens -----------------------------------------------

    def create_verification_token(self, token: VerificationToken) -> VerificationToken:
        """Insert a verification token and return it with its new id."""
        with self._session_factory() as db:
            row = TokenRow(
                user_id=token.user_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                used_at=_stamp(token.used, None),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _token(row)

    def find_verification_token(self, token_hash: str) -> VerificationToken | None:
        """Return the token whose link hashes to this value, if any."""
        with self._session_factory() as db:
            row = db.exec(
                select(TokenRow).where(TokenRow.token_hash == token_hash)
            ).first()
            if row is None:
                return None
            return _token(row)

    def update_verification_token(self, token: VerificationToken) -> VerificationToken:
        """Replace an existing token and return the stored value."""
        with self._session_factory() as db:
            row = db.get(TokenRow, token.id)
            if row is None:
                raise KeyError(token.id)
            row.expires_at = token.expires_at
            row.used_at = _stamp(token.used, row.used_at)
            db.commit()
            db.refresh(row)
            return _token(row)

    # ---- instructor requests -----------------------------------------------

    def create_instructor_request(
        self, request: InstructorRequest
    ) -> InstructorRequest:
        """Insert an Instructor request and return it with its new id."""
        with self._session_factory() as db:
            row = InstructorRequestRow(
                user_id=request.user_id,
                faculty=request.faculty,
                requested_at=request.requested_at,
                status=request.status.value,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _request(row)

    def list_instructor_requests(
        self, status: InstructorRequestStatus
    ) -> list[InstructorRequest]:
        """Return the requests in this status, in id order."""
        with self._session_factory() as db:
            rows = db.exec(
                select(InstructorRequestRow)
                .where(InstructorRequestRow.status == status.value)
                .order_by(InstructorRequestRow.id)
            ).all()
            return [_request(row) for row in rows]

    def find_pending_instructor_request(self, user_id: int) -> InstructorRequest | None:
        """Return this account's pending request, if it has one."""
        with self._session_factory() as db:
            row = db.exec(
                select(InstructorRequestRow)
                .where(
                    InstructorRequestRow.user_id == user_id,
                    InstructorRequestRow.status
                    == InstructorRequestStatus.PENDING.value,
                )
                .order_by(InstructorRequestRow.id)
            ).first()
            if row is None:
                return None
            return _request(row)
