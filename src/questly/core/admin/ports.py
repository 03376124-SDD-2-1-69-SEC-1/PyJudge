from typing import Protocol

from questly.core.admin.models import AISettings, SystemStatus


class AdminRepository(Protocol):
    def get_ai_settings(self) -> AISettings:
        """อ่านค่า AI settings ปัจจุบัน."""
        ...

    def update_ai_settings(self, settings: AISettings) -> AISettings:
        """แทนที่ AI settings ทั้งแถวด้วยค่าที่ส่งมา แล้วคืนค่าที่บันทึก."""
        ...

    def get_usage_this_month(self) -> int:
        """นับการใช้งานเดือนปัจจุบันจาก generation events."""
        ...


class SystemHealthChecker(Protocol):
    def check_services_health(self) -> SystemStatus:
        """ตรวจสอบสถานะบริการทั้ง 6 ตัว."""
        ...
