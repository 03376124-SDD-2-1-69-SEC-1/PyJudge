"""SQL adapter for the AdminRepository port (OPS-22)."""

from questly.core.admin.models import AISettings
from questly.database.core.tables import AiSettings as AiSettingsRow
from questly.database.session import SessionFactory


class SQLAdminRepository:
    """Read and replace the singleton `core.ai_settings` row."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def get_ai_settings(self) -> AISettings:
        with self._session_factory() as session:
            row = session.get(AiSettingsRow, 1)
            if row is None:
                raise RuntimeError("core.ai_settings singleton row is missing")
            return AISettings(
                model=row.model,
                daily_quota=row.daily_quota,
                max_pages=row.max_pages,
                require_citations=row.require_citations,
            )

    def update_ai_settings(self, settings: AISettings) -> AISettings:
        with self._session_factory() as session:
            row = session.get(AiSettingsRow, 1)
            if row is None:
                raise RuntimeError("core.ai_settings singleton row is missing")
            row.model = settings.model
            row.daily_quota = settings.daily_quota
            row.max_pages = settings.max_pages
            row.require_citations = settings.require_citations
            session.commit()
            session.refresh(row)
            return AISettings(
                model=row.model,
                daily_quota=row.daily_quota,
                max_pages=row.max_pages,
                require_citations=row.require_citations,
            )
