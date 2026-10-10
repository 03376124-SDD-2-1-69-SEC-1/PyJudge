"""SQL adapter for the AdminRepository port (OPS-22)."""

from sqlalchemy import func
from sqlmodel import select

from questly.core.admin.domain import AISettings, AISettingsUpdate
from questly.database.core.tables import AiSettings as AiSettingsRow
from questly.database.core.tables import GenerationEvent
from questly.database.session import SessionFactory


class SQLAdminRepository:
    """Read and update the singleton AI settings row and usage totals."""

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

    def update_ai_settings(self, settings: AISettingsUpdate) -> AISettings:
        with self._session_factory() as session:
            row = session.get(AiSettingsRow, 1)
            if row is None:
                raise RuntimeError("core.ai_settings singleton row is missing")
            if settings.model is not None:
                row.model = settings.model
            if settings.daily_quota is not None:
                row.daily_quota = settings.daily_quota
            if settings.max_pages is not None:
                row.max_pages = settings.max_pages
            if settings.require_citations is not None:
                row.require_citations = settings.require_citations
            session.commit()
            session.refresh(row)
            return AISettings(
                model=row.model,
                daily_quota=row.daily_quota,
                max_pages=row.max_pages,
                require_citations=row.require_citations,
            )

    def get_usage_this_month(self) -> int:
        with self._session_factory() as session:
            return session.exec(
                select(func.count())
                .select_from(GenerationEvent)
                .where(
                    GenerationEvent.occurred_at >= func.date_trunc("month", func.now())
                )
            ).one()
