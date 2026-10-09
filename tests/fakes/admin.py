from questly.config import DEFAULT_GENERATION_MODEL
from questly.core.admin.domain import (
    AISettings,
    AISettingsUpdate,
    ServiceHealthStatus,
    ServiceStatus,
    SystemStatusResponse,
)
from questly.core.admin.ports import AdminRepository, SystemHealthChecker


class FakeAdminRepository(AdminRepository):
    def __init__(self, initial_settings: AISettings | None = None):
        self.settings = initial_settings or AISettings(
            model=DEFAULT_GENERATION_MODEL,
            daily_quota=20,
            max_pages=10,
            require_citations=True,
            usage_this_month=5,
        )
        self.usage_this_month = self.settings.usage_this_month

    def get_ai_settings(self) -> AISettings:
        return self.settings

    def update_ai_settings(self, settings: AISettingsUpdate) -> AISettings:
        current_dict = self.settings.model_dump()
        update_data = settings.model_dump(exclude_unset=True)
        current_dict.update(update_data)
        self.settings = AISettings(**current_dict)
        return self.settings

    def get_usage_this_month(self) -> int:
        return self.usage_this_month


class FakeSystemHealthChecker(SystemHealthChecker):
    def __init__(self, is_healthy: bool = True):
        self.is_healthy = is_healthy

    def check_services_health(self) -> SystemStatusResponse:
        status = (
            ServiceHealthStatus.HEALTHY
            if self.is_healthy
            else ServiceHealthStatus.UNHEALTHY
        )
        services = [
            ServiceStatus(name="web application", status=status),
            ServiceStatus(name="database", status=status),
            ServiceStatus(name="PDF processing", status=status),
            ServiceStatus(name="AI generation", status=status),
            ServiceStatus(name="code execution sandbox", status=status),
            ServiceStatus(name="email delivery", status=status),
        ]
        return SystemStatusResponse(services=services)
