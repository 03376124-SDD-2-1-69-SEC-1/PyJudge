"""The one place GReader reads its environment.

Every other module takes a `Settings` instance instead of touching `os.environ`,
so importing `greader.main` never depends on a populated `.env` and a test can
build an app without one. `get_settings()` reads the environment when it is
called, not when this module is imported.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

DEFAULT_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024

REQUIRED_DRIVER = "postgresql+psycopg"


class MissingConfigurationError(RuntimeError):
    """Raised when a required environment variable is absent or unusable."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Everything GReader needs from its environment, resolved once."""

    database_url: str
    r2_endpoint_url: str
    r2_bucket_name: str
    r2_access_key_id: str
    r2_secret_access_key: str
    max_upload_size_bytes: int = DEFAULT_MAX_UPLOAD_SIZE_BYTES


def _required(variable: str) -> str:
    value = os.environ.get(variable, "").strip()
    if not value:
        raise MissingConfigurationError(
            f"{variable} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _upload_size_limit() -> int:
    raw = os.environ.get("MAX_UPLOAD_SIZE_BYTES", "").strip()
    if not raw:
        return DEFAULT_MAX_UPLOAD_SIZE_BYTES
    if not raw.isdigit() or int(raw) <= 0:
        raise MissingConfigurationError(
            f"MAX_UPLOAD_SIZE_BYTES must be a positive integer, got {raw!r}."
        )
    return int(raw)


def _database_url() -> str:
    """Return the DSN, refusing anything SQLAlchemy would resolve to psycopg2.

    Only psycopg v3 is a project dependency, and a bare `postgresql://` URL
    fails later with an unhelpful `NoSuchModuleError`.
    """
    url = _required("DATABASE_URL")
    scheme, separator, _ = url.partition("://")
    if not separator:
        raise MissingConfigurationError("DATABASE_URL is not a database URL.")
    if scheme != REQUIRED_DRIVER:
        raise MissingConfigurationError(
            f"DATABASE_URL must use {REQUIRED_DRIVER}://, got {scheme}://"
        )
    return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read the environment once and return the resolved configuration."""
    load_dotenv()
    return Settings(
        database_url=_database_url(),
        r2_endpoint_url=_required("R2_ENDPOINT_URL"),
        r2_bucket_name=_required("R2_BUCKET_NAME"),
        r2_access_key_id=_required("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        max_upload_size_bytes=_upload_size_limit(),
    )
