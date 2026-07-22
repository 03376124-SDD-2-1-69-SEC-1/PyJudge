"""Safe application errors for assignment generation."""

from __future__ import annotations

SAFE_PROVIDER_ERROR_CODES = {
    "provider_timeout",
    "provider_authentication_failed",
    "provider_rate_limited",
    "provider_invalid_response",
    "provider_unavailable",
}


class GenerationError(Exception):
    """Generation failure that exposes only a safe error code."""

    def __init__(self, safe_error_code: str) -> None:
        self.safe_error_code = safe_error_code
        super().__init__(safe_error_code)

    def __str__(self) -> str:
        """Return only the safe error code."""
        return self.safe_error_code


class GeminiConfigurationError(GenerationError):
    """Gemini provider is selected but not safely configured."""

    def __init__(self) -> None:
        super().__init__("provider_authentication_failed")
