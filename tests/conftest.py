"""Guards for the only tests allowed to reach a real PostgreSQL database.

Tests marked `postgres` connect to a throwaway Neon branch created by CI and
deleted when the run ends. They read `POSTGRES_TEST_URL` and nothing else:
`DATABASE_URL` points at the branch the whole team develops against, and these
tests insert and delete rows.

Locally the marked tests skip themselves, so `uv run pytest` stays green on a
machine with no test database. In CI the variable must be present, otherwise a
failed branch step would leave every `postgres` test skipped and the run green
while nothing was verified.
"""

import os
from urllib.parse import urlsplit

import pytest

TEST_URL_VAR = "POSTGRES_TEST_URL"
SHARED_URL_VARS = ("DATABASE_URL", "DATABASE_URL_UNPOOLED")
REQUIRED_DRIVER = "postgresql+psycopg"


def _running_in_ci() -> bool:
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}


def _with_psycopg_driver(url: str) -> str:
    """Return the DSN with the +psycopg tag the project requires.

    The Neon CLI prints `postgresql://…`, and SQLAlchemy resolves a bare
    `postgresql://` to psycopg2, which is not a project dependency.
    """
    scheme, separator, rest = url.partition("://")
    if not separator:
        pytest.fail(f"{TEST_URL_VAR} is not a database URL")
    if scheme == REQUIRED_DRIVER:
        return url
    if scheme in {"postgres", "postgresql"}:
        return f"{REQUIRED_DRIVER}://{rest}"
    pytest.fail(f"{TEST_URL_VAR} must use {REQUIRED_DRIVER}://, got {scheme}://")


def _endpoint(url: str) -> str | None:
    """Identify the compute a DSN points at, ignoring Neon's pooler suffix.

    `ep-x-pooler.region.neon.tech` and `ep-x.region.neon.tech` are two doors
    into one database, so both must compare equal.
    """
    host = urlsplit(url).hostname
    if host is None:
        return None
    label, separator, domain = host.partition(".")
    label = label.removesuffix("-pooler")
    return f"{label}{separator}{domain}"


def _reject_shared_database(url: str) -> None:
    target = _endpoint(url)
    for variable in SHARED_URL_VARS:
        shared = os.environ.get(variable)
        if shared and _endpoint(shared) == target:
            pytest.fail(
                f"{TEST_URL_VAR} points at the same compute as {variable}. "
                "These tests write and delete rows; point it at a throwaway "
                "Neon branch instead."
            )


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """Return the DSN of the throwaway database, or fail explaining why not."""
    url = os.environ.get(TEST_URL_VAR)
    if not url:
        pytest.fail(
            f"{TEST_URL_VAR} is unset. In CI this means the Neon branch step "
            "did not run, so no database test verified anything."
        )
    url = _with_psycopg_driver(url)
    _reject_shared_database(url)
    return url


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip database tests locally; let them run and fail loudly in CI."""
    if os.environ.get(TEST_URL_VAR) or _running_in_ci():
        return
    skip = pytest.mark.skip(reason=f"needs {TEST_URL_VAR}; see .env.example")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)
