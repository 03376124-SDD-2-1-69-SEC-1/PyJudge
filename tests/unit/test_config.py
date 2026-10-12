"""GENERATION_MODEL_ALLOWLIST parsing in get_settings()."""

from collections.abc import Generator

import pytest

from questly import config


@pytest.fixture(autouse=True)
def required_environment(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    config.get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("GENERATION_MODEL", "configured/model")
    yield
    config.get_settings.cache_clear()


def test_unset_allowlist_allows_only_the_generation_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENERATION_MODEL_ALLOWLIST", "")

    assert config.get_settings().generation_model_allowlist == ("configured/model",)


def test_allowlist_is_comma_separated_and_trimmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GENERATION_MODEL_ALLOWLIST", " a/one , b/two:free,, ")

    assert config.get_settings().generation_model_allowlist == ("a/one", "b/two:free")
