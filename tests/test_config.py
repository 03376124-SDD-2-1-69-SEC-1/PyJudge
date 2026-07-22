"""Tests for environment-based application settings."""

from greader.config import Settings


def test_database_url_override_wins(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///:memory:"


def test_database_url_builds_postgres_url_from_parts(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "reader")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s@cret/word")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "greader_test")

    settings = Settings(_env_file=None)

    assert (
        settings.database_url
        == "postgresql+psycopg://reader:s%40cret%2Fword@db:5432/greader_test"
    )
