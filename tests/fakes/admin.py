from questly.config import DEFAULT_GENERATION_MODEL
from questly.core.admin.models import (
    AISettings,
    ServiceHealthStatus,
    ServiceStatus,
    SystemStatus,
)

DEFAULT_AI_SETTINGS = AISettings(
    model=DEFAULT_GENERATION_MODEL,
    daily_quota=20,
    max_pages=10,
    require_citations=True,
)


class FakeAdminRepository:
    def __init__(self, settings: AISettings = DEFAULT_AI_SETTINGS) -> None:
        self.settings = settings

    def get_ai_settings(self) -> AISettings:
        return self.settings

    def update_ai_settings(self, settings: AISettings) -> AISettings:
        self.settings = settings
        return self.settings


class FakeSystemHealthChecker:
    """All six services up, all down, or only the names in `down` down."""

    def __init__(self, is_healthy: bool = True, down: tuple[str, ...] = ()) -> None:
        self.is_healthy = is_healthy
        self.down = down

    def check_services_health(self) -> SystemStatus:
        status = (
            ServiceHealthStatus.HEALTHY
            if self.is_healthy
            else ServiceHealthStatus.UNHEALTHY
        )
        names = (
            "web application",
            "database",
            "PDF processing",
            "AI generation",
            "code execution sandbox",
            "email delivery",
        )
        return SystemStatus(
            services=[
                ServiceStatus(
                    name=name,
                    status=ServiceHealthStatus.UNHEALTHY
                    if name in self.down
                    else status,
                )
                for name in names
            ]
        )
