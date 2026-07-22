"""Provider factory and safe AI connection status."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from greader.assistant.demo import DemoAssignmentGenerator
from greader.assistant.errors import GeminiConfigurationError, GenerationError
from greader.assistant.gemini import GeminiAssignmentGenerator
from greader.assistant.interface import AssignmentGenerator
from greader.config import Settings


class AIConnectionStatus(BaseModel):
    """Safe provider status for display."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model_name: str
    configured: bool

    def __eq__(self, other: object) -> bool:
        """Allow tests and callers to compare with a plain status dict."""
        if isinstance(other, dict):
            return self.model_dump() == other
        return super().__eq__(other)


def build_assignment_generator(settings: Settings) -> AssignmentGenerator:
    """Build the configured assignment generator."""
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == "demo":
        return DemoAssignmentGenerator()
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise GeminiConfigurationError()
        return GeminiAssignmentGenerator(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL,
            timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
        )
    raise GenerationError("provider_unavailable")


def ai_connection_status(settings: Settings) -> AIConnectionStatus:
    """Return provider status without exposing any secret value."""
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == "gemini":
        return AIConnectionStatus(
            provider="gemini",
            model_name=settings.GEMINI_MODEL,
            configured=bool(settings.GEMINI_API_KEY),
        )
    if provider == "demo":
        return AIConnectionStatus(provider="demo", model_name="demo", configured=True)
    return AIConnectionStatus(
        provider=provider or "unknown",
        model_name="unknown",
        configured=False,
    )
