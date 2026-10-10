"""Email adapter. The stub records messages for local development."""

import logging

logger = logging.getLogger("questly.email")


class StubEmailSender:
    """Capture outgoing emails without requiring a mail server."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.messages: list[dict[str, str]] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Record an email sent through the notification email port."""
        self.messages.append({"to": to, "subject": subject, "body": body})
        self.sent.append((to, body))
        logger.warning("email to %s: %s", to, subject)
