"""Shared test fixtures for GReader tests."""

import os

import pytest
from sqlalchemy.orm import sessionmaker

from greader.database import build_engine
from greader.db_models import Base


@pytest.fixture()
def test_engine():
    """Create an in-memory SQLite engine for tests."""
    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def test_session_factory(test_engine):
    """Return a sessionmaker bound to the in-memory test engine."""
    return sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    """Ensure tests never hit the production database."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AI_PROVIDER", "demo")


def pytest_configure(config):
    """Set environment to 'test' early, before any imports."""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("AI_PROVIDER", "demo")
