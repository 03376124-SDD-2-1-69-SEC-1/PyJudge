from typing import Protocol

from questly.core.admin.domain import (
    AISettings,
    AISettingsUpdate,
    SystemStatusResponse,
)


class AdminRepository(Protocol):
    def get_ai_settings(self) -> AISettings:
        """อ่านค่า AI settings ปัจจุบัน."""
        ...

    def update_ai_settings(self, settings: AISettingsUpdate) -> AISettings:
        """อัปเดต AI settings."""
        ...

    def get_usage_this_month(self) -> int:
        """นับการใช้งานเดือนปัจจุบันจาก generation events."""
        ...


class SystemHealthChecker(Protocol):
    def check_services_health(self) -> SystemStatusResponse:
        """ตรวจสอบสถานะบริการทั้ง 6 ตัว."""
        ...
