"""AI-01 regression checks: vector wiring never touches real infrastructure
unless every other adapter is also left to its SQL/R2 default.
"""

import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from greader import config, main
from greader.database import session
from greader.database.rag import vector_repository as postgres_adapter
from greader.database.storage import r2


@pytest.fixture(autouse=True)
def isolated_settings_cache():
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_fresh_import_and_injected_app_never_initialize_infrastructure() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DATABASE_", "R2_", "AWS_"))
    }
    code = """
from unittest.mock import patch
with patch('sqlmodel.create_engine', side_effect=AssertionError('engine constructed')):
    with patch('boto3.client', side_effect=AssertionError('client constructed')):
        with patch('socket.socket.connect', side_effect=AssertionError('connection')):
            from tests.fakes.app import build_app
            app = build_app()
            assert app.state.vector_service is not None
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0, result.stderr


def test_missing_database_url_fails_loudly_before_any_connection(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")
    with pytest.raises(config.MissingConfigurationError, match="DATABASE_URL"):
        config.get_settings()


def test_settings_are_resolved_once_and_reused(monkeypatch) -> None:
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")
    assert config.get_settings() is config.get_settings()


def test_production_composition_wires_the_postgres_vector_repository(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")

    repository = Mock()
    adapter_factory = Mock(return_value=repository)
    monkeypatch.setattr(main, "PostgresVectorRepository", adapter_factory)
    monkeypatch.setattr(session, "create_engine", Mock(return_value=object()))
    monkeypatch.setattr(r2, "boto3", Mock())

    application = main.create_app()

    assert application.state.vector_service._repository is repository
    adapter_factory.assert_called_once()


def test_postgres_repository_rejects_non_psycopg_urls() -> None:
    with pytest.raises(RuntimeError, match="postgresql\\+psycopg"):
        postgres_adapter.create_postgres_repository("sqlite:///test.db")
