"""Tests that the migration chain matches the current persistence model."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_head_uses_explicit_artifact_review_state(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config("alembic.ini")

    command.upgrade(config, "head")

    columns = {
        column["name"]
        for column in inspect(create_engine(database_url)).get_columns(
            "generation_artifacts"
        )
    }
    assert "review_status" in columns
    assert "reviewed_at" in columns
    assert "is_applied" not in columns
    assert "applied_at" not in columns
