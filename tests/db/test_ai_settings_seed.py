"""After `alembic upgrade head`, the AI settings row names OpenRouter (OPS-23)."""

import pytest
from sqlalchemy import text

from questly.database.session import SessionFactory

pytestmark = pytest.mark.postgres


def test_ai_settings_seed_uses_openrouter(session_factory: SessionFactory) -> None:
    with session_factory() as session:
        provider = session.execute(
            text("SELECT provider FROM core.ai_settings WHERE id = 1")
        ).scalar_one()

    assert provider == "openrouter"
