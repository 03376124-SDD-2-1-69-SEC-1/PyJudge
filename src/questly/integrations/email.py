"""Email adapter. The stub records and logs messages instead of sending them."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("questly.email")


@dataclass(frozen=True, slots=True)
class SentEmail:
    to: str
    subject: str
    body: str


class StubEmailSender:
    """Capture outgoing emails without requiring a mail server.

    The whole body is logged so a verification link can be followed in demo
    mode (scripts/demo.py promises that).
    """

    def __init__(self) -> None:
        self.messages: list[SentEmail] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        """Record an email sent through the notification email port."""
        self.messages.append(SentEmail(to=to, subject=subject, body=body))
        logger.warning("email to %s: %s\n%s", to, subject, body)
