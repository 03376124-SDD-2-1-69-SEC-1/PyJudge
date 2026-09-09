"""AI-01 regression checks for lazy production infrastructure."""

import os
import subprocess
import sys
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from greader import main
from greader.database import session, storage


@pytest.fixture(autouse=True)
def isolated_factories(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    session.get_engine.cache_clear()
    storage.get_r2_storage.cache_clear()
    yield
    session.get_engine.cache_clear()
    storage.get_r2_storage.cache_clear()


def test_fresh_import_and_test_app_never_initialize_infrastructure() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("DATABASE_", "R2_", "AWS_"))
    }
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    code = """
from unittest.mock import patch
with patch('sqlmodel.create_engine', side_effect=AssertionError('engine constructed')):
    with patch('boto3.client', side_effect=AssertionError('client constructed')):
        with patch('socket.socket.connect', side_effect=AssertionError('connection')):
            from greader.main import create_app, create_production_app
            from greader.ai.app.repository import InMemoryVectorRepository
            app = create_app(vector_repository=InMemoryVectorRepository())
            assert app.state.vector_service is not None
            assert create_production_app().state.vector_service is not None
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_engine_initialization_is_deferred_and_cached(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    factory = Mock(return_value=object())
    monkeypatch.setattr(session, "create_engine", factory)
    assert session.get_engine() is session.get_engine()
    factory.assert_called_once()
    assert factory.call_args.args[0].drivername == "postgresql+psycopg"
    assert factory.call_args.kwargs == {"echo": False}


@pytest.mark.parametrize("url", [None, "", "sqlite:///test.db", "invalid"])
def test_missing_or_invalid_database_configuration_fails_on_use(monkeypatch, url):
    if url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        session.get_engine()


def test_r2_initialization_preserves_configuration_and_is_cached(monkeypatch):
    settings = {
        "R2_ENDPOINT_URL": "https://example.r2.cloudflarestorage.com",
        "R2_BUCKET_NAME": "test-bucket",
        "R2_ACCESS_KEY_ID": "test-key",
        "R2_SECRET_ACCESS_KEY": "test-secret",
    }
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    factory = Mock(return_value=Mock())
    monkeypatch.setattr(storage.boto3, "client", factory)
    configured = storage.get_r2_storage()
    client = configured.client
    assert storage.get_r2_storage() is configured
    factory.assert_called_once()
    assert factory.call_args.args == ("s3",)
    options = factory.call_args.kwargs
    assert options["endpoint_url"] == settings["R2_ENDPOINT_URL"]
    assert options["aws_access_key_id"] == settings["R2_ACCESS_KEY_ID"]
    assert options["aws_secret_access_key"] == settings["R2_SECRET_ACCESS_KEY"]
    assert options["config"].signature_version == "s3v4"
    assert options["region_name"] == "auto"
    monkeypatch.delenv("R2_BUCKET_NAME")
    assert storage.check_r2(configured) == {"connected": True, "bucket": "test-bucket"}
    client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    assert storage.upload_file(configured, "local.pdf", "uploads/original.pdf") == {
        "bucket": "test-bucket",
        "key": "uploads/original.pdf",
    }
    client.upload_file.assert_called_once_with(
        "local.pdf", "test-bucket", "uploads/original.pdf"
    )


@pytest.mark.parametrize(
    "missing",
    ["R2_ENDPOINT_URL", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"],
)
def test_missing_r2_configuration_fails_before_client_construction(
    monkeypatch, missing
):
    for name, value in {
        "R2_ENDPOINT_URL": "https://example.r2.cloudflarestorage.com",
        "R2_BUCKET_NAME": "test-bucket",
        "R2_ACCESS_KEY_ID": "test-key",
        "R2_SECRET_ACCESS_KEY": "test-secret",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(missing)
    factory = Mock()
    monkeypatch.setattr(storage.boto3, "client", factory)
    with pytest.raises(RuntimeError, match=f"{missing} is required"):
        storage.get_r2_storage()
    factory.assert_not_called()


@pytest.mark.parametrize("bucket", ["", "   "])
def test_storage_configuration_rejects_empty_bucket(bucket):
    with pytest.raises(ValueError, match="nonempty bucket"):
        storage.R2Storage(client=Mock(), bucket=bucket)


def test_upload_limit_respects_deferred_dotenv_configuration(monkeypatch):
    monkeypatch.delenv("MAX_UPLOAD_SIZE_BYTES", raising=False)
    monkeypatch.setattr(
        storage,
        "load_dotenv",
        lambda: monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "123"),
    )
    assert storage.get_max_upload_size_bytes() == 123


def test_production_composition_defers_real_session_factory(monkeypatch):
    repository = Mock()
    adapter_factory = Mock(return_value=repository)
    engine_factory = Mock(return_value=object())
    session_factory = Mock(return_value=object())
    monkeypatch.setattr(main, "PostgresVectorRepository", adapter_factory)
    monkeypatch.setattr(main, "get_engine", engine_factory)
    monkeypatch.setattr(main, "Session", session_factory)
    application = main.create_production_app()
    assert application.state.vector_service._repository is repository
    engine_factory.assert_not_called()
    session_factory.assert_not_called()
    supplied_factory = adapter_factory.call_args.args[0]
    assert supplied_factory() is session_factory.return_value
    session_factory.assert_called_once_with(engine_factory.return_value)


def test_health_checks_keep_dependency_overrides_and_failure_status(monkeypatch):
    application = main.create_app()
    db_session = Mock()
    r2_client = Mock()
    application.dependency_overrides[session.get_session] = lambda: db_session
    application.dependency_overrides[storage.get_r2_storage] = lambda: (
        storage.R2Storage(client=r2_client, bucket="test-bucket")
    )
    check_db = Mock(return_value={"connected": True})
    monkeypatch.setattr(main, "check_db", check_db)
    monkeypatch.delenv("R2_BUCKET_NAME", raising=False)
    with TestClient(application) as client:
        assert client.get("/health/db").json() == {"connected": True}
        assert client.get("/health/r2").json() == {
            "connected": True,
            "bucket": "test-bucket",
        }
        check_db.assert_called_once_with(db_session)
        r2_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
        check_db.side_effect = RuntimeError("database unavailable")
        r2_client.head_bucket.side_effect = RuntimeError("storage unavailable")
        assert client.get("/health/db").status_code == 503
        assert client.get("/health/r2").status_code == 503
