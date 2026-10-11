"""The helpers behind scripts/run_integration_tests.py.

The script itself needs Neon and R2, so only its pure decisions are tested here:
which DSN reaches SQLAlchemy, which R2 prefix a run owns, which tests it selects.
"""

import pytest
from scripts.run_integration_tests import (
    marker_expression,
    new_run_id,
    r2_prefix,
    to_psycopg_dsn,
)

from questly.database.storage.safety import assert_safe_prefix


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql://u:p@host/db?sslmode=require\n",
        "postgres://u:p@host/db?sslmode=require",
        "postgresql+psycopg://u:p@host/db?sslmode=require",
    ],
)
def test_dsn_always_names_the_psycopg_driver(raw: str) -> None:
    assert to_psycopg_dsn(raw) == "postgresql+psycopg://u:p@host/db?sslmode=require"


@pytest.mark.parametrize("raw", ["", "not a url", "mysql://u:p@host/db"])
def test_dsn_rejects_anything_that_is_not_postgres(raw: str) -> None:
    with pytest.raises(ValueError):
        to_psycopg_dsn(raw)


def test_every_run_owns_a_distinct_prefix_the_r2_guard_accepts() -> None:
    first, second = r2_prefix(new_run_id()), r2_prefix(new_run_id())

    assert first != second
    assert_safe_prefix(first)
    assert_safe_prefix(second)


def test_marker_expression_selects_only_the_requested_groups() -> None:
    assert marker_expression(["postgres", "r2"]) == "postgres or r2"
    assert marker_expression(["r2"]) == "r2"
