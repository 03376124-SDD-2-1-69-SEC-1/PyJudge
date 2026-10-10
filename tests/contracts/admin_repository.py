import pytest
from pydantic import ValidationError

from questly.core.admin.domain import AISettingsUpdate
from questly.core.admin.ports import AdminRepository


class AdminRepositoryContractTests:
    """Contract tests for AdminRepository implementations (Fake & SQL)."""

    def test_get_and_update_ai_settings(self, repo: AdminRepository) -> None:
        settings = repo.get_ai_settings()
        assert settings.daily_quota > 0
        assert settings.model is not None

        updated = repo.update_ai_settings(AISettingsUpdate(daily_quota=50))
        assert updated.daily_quota == 50
        assert updated.model == settings.model
        assert updated.max_pages == settings.max_pages
        assert updated.require_citations == settings.require_citations

    def test_get_usage_this_month(self, repo: AdminRepository) -> None:
        usage = repo.get_usage_this_month()
        assert usage >= 0

    def test_settings_updates_reject_explicit_nulls(self) -> None:
        with pytest.raises(ValidationError):
            AISettingsUpdate(model=None)
