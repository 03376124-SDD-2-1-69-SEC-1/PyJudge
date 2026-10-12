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
    def __init__(
        self, settings: AISettings = DEFAULT_AI_SETTINGS, usage_this_month: int = 5
    ) -> None:
        self.settings = settings
        self.usage_this_month = usage_this_month

    def get_ai_settings(self) -> AISettings:
        return self.settings

    def update_ai_settings(self, settings: AISettings) -> AISettings:
        self.settings = settings
        return self.settings

    def get_usage_this_month(self) -> int:
        return self.usage_this_month


class FakeSystemHealthChecker:
    def __init__(self, is_healthy: bool = True) -> None:
        self.is_healthy = is_healthy

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
            services=[ServiceStatus(name=name, status=status) for name in names]
        )
