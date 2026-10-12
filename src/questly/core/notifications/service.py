"""Business logic for user notifications (ADR-0007 §6)."""

from questly.core.auth.ports import Clock
from questly.core.notifications.models import (
    Notification,
    NotificationKind,
    NotificationPayload,
)
from questly.core.notifications.ports import (
    ClassroomMembers,
    EmailSender,
    NotificationRepository,
    UserAccounts,
)

_SUBJECTS = {
    NotificationKind.ASSIGNMENT_PUBLISHED: "New problem: {title}",
    NotificationKind.ASSIGNMENT_UPDATED: "Problem updated: {title}",
    NotificationKind.ASSIGNMENT_NOTIFIED: "Reminder: {title}",
}


class NotificationNotFoundError(Exception):
    """Raised when a notification does not exist for the requested user."""


class NotificationService:
    """Coordinate notification storage, read state, and email delivery."""

    def __init__(
        self,
        repository: NotificationRepository,
        email_sender: EmailSender,
        clock: Clock,
        members: ClassroomMembers,
        accounts: UserAccounts,
    ) -> None:
        self._repository = repository
        self._email_sender = email_sender
        self._clock = clock
        self._members = members
        self._accounts = accounts

    def list_for_user(self, user_id: int) -> list[Notification]:
        """List a user's notifications, newest first."""
        return self._repository.list_for_user(user_id)

    def mark_read(
        self,
        user_id: int,
        notification_id: int,
    ) -> Notification:
        """Mark a notification as read only if it belongs to the user."""
        notification = self._repository.get(notification_id)

        if notification is None or notification.user_id != user_id:
            raise NotificationNotFoundError

        if notification.read_at is not None:
            return notification

        return self._repository.mark_read(
            notification_id,
            read_at=self._clock.now(),
        )

    def mark_all_read(self, user_id: int) -> int:
        """Mark every unread notification belonging to the user as read."""
        return self._repository.mark_all_read(
            user_id,
            read_at=self._clock.now(),
        )

    def create(
        self,
        *,
        user_id: int,
        kind: NotificationKind,
        payload: NotificationPayload,
    ) -> Notification:
        """Persist a notification for one user."""
        return self._repository.create(
            Notification(
                user_id=user_id,
                kind=kind,
                payload=payload,
                created_at=self._clock.now(),
            )
        )

    def notify_members(
        self,
        classroom_id: int,
        kind: NotificationKind,
        payload: NotificationPayload,
    ) -> None:
        """Store one notification per Member and email each of them.

        The caller has already decided the Actor may notify this Classroom.
        `payload` carries `classroom_id`, `assignment_id`, `title` and, for an
        update, `reason`.
        """
        subject = _SUBJECTS[kind].format(title=payload["title"])
        for membership in self._members.list_memberships(classroom_id):
            self.create(user_id=membership.student_id, kind=kind, payload=payload)
            user = self._accounts.get_user(membership.student_id)
            if user is None:
                continue
            self.send_email(
                to=user.email,
                subject=subject,
                body=_member_email(user.full_name, subject, payload),
            )

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        body: str,
    ) -> None:
        """Send an email through the notification-owned email port."""
        self._email_sender.send(to=to, subject=subject, body=body)


def _member_email(full_name: str, subject: str, payload: NotificationPayload) -> str:
    lines = [f"Hi {full_name},", "", subject]
    if "reason" in payload:
        lines.append(f"Reason from your instructor: {payload['reason']}")
    lines += [
        "",
        f"/classes/{payload['classroom_id']}/assignments/{payload['assignment_id']}",
    ]
    return "\n".join(lines)
