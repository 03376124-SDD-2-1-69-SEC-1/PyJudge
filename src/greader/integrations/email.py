"""Email adapters. The stub logs instead of sending (ADR-0007: stubs first)."""

import logging

logger = logging.getLogger("greader.email")


class StubEmailSender:
    """Records every message and logs verification links for local use."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_verification(
        self, *, email: str, full_name: str, verify_path: str
    ) -> None:
        """Satisfy auth's VerificationMailer without a mail server."""
        self.sent.append((email, verify_path))
        logger.warning(
            "verification link for %s <%s>: %s", full_name, email, verify_path
        )
