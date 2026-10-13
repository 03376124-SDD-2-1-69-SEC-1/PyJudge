"""Run the `postgres` and `r2` tests against throwaway infrastructure.

    uv run --env-file .env python -m scripts.run_integration_tests
    uv run --env-file .env python -m scripts.run_integration_tests --only postgres
    uv run --env-file .env python -m scripts.run_integration_tests -- -k classroom

CI no longer runs these. They talk to real Neon and R2 from a hosted runner on
another continent, which made the pipeline take ten minutes. Run this before
opening a PR that touches `database/`, `alembic/`, `tests/db/` or `tests/r2/`.

What it does, in order:

1. Creates a Neon branch off `NEON_PARENT_BRANCH` (default `production`) that
   expires on its own after two hours, so a killed run cannot leak it.
2. Applies `alembic upgrade head` to that branch only. `DATABASE_URL` and
   `DATABASE_URL_UNPOOLED` are overridden for the subprocess, so the shared
   database is never the target.
3. Runs pytest on the `postgres` and `r2` markers with `POSTGRES_TEST_URL` and
   a unique `R2_TEST_PREFIX` set.
4. Deletes the branch and every R2 object under the run's prefix, whether the
   tests passed or not.

Needs the `neonctl` CLI (or `npx`), `NEON_PROJECT_ID`, and for R2 the four
`R2_TEST_*` variables from README "Integration tests".
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta

POSTGRES = "postgres"
R2 = "r2"
R2_TEST_VARS = (
    "R2_TEST_ENDPOINT_URL",
    "R2_TEST_ACCESS_KEY_ID",
    "R2_TEST_SECRET_ACCESS_KEY",
    "R2_TEST_BUCKET_NAME",
)
BRANCH_LIFETIME = timedelta(hours=2)


def to_psycopg_dsn(raw: str) -> str:
    """Return the DSN with the +psycopg driver tag the project requires.

    neonctl prints a bare `postgresql://`, which SQLAlchemy resolves to
    psycopg2, and psycopg2 is not installed.
    """
    scheme, separator, rest = raw.strip().partition("://")
    if not separator or scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("neonctl did not return a PostgreSQL connection string")
    return f"postgresql+psycopg://{rest}"


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def r2_prefix(run_id: str) -> str:
    """Key prefix this run owns; `local/` is one of the roots `safety.py` allows."""
    return f"local/{run_id}/"


def marker_expression(targets: list[str]) -> str:
    return " or ".join(targets)


def _neonctl() -> list[str]:
    if shutil.which("neonctl"):
        return ["neonctl"]
    if shutil.which("npx"):
        return ["npx", "-y", "neonctl"]
    sys.exit("neonctl not found. Install it with `npm i -g neonctl` (needs Node).")


def _run(command: list[str], env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        command, check=True, text=True, capture_output=True, env=env
    ).stdout


def create_branch(project_id: str, parent: str, name: str) -> str:
    expires = (datetime.now(UTC) + BRANCH_LIFETIME).strftime("%Y-%m-%dT%H:%M:%SZ")
    _run(
        [
            *_neonctl(),
            "branches",
            "create",
            "--project-id",
            project_id,
            "--name",
            name,
            "--parent",
            parent,
            "--expires-at",
            expires,
        ]
    )
    raw = _run([*_neonctl(), "connection-string", name, "--project-id", project_id])
    return to_psycopg_dsn(raw)


def delete_branch(project_id: str, name: str) -> None:
    result = subprocess.run(
        [*_neonctl(), "branches", "delete", name, "--project-id", project_id],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"warning: could not delete branch {name}; it expires on its own")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--only",
        choices=[POSTGRES, R2],
        help="run just one of the two marked groups",
    )
    parser.add_argument(
        "--keep-branch",
        action="store_true",
        help="leave the Neon branch in place for debugging (it still expires)",
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("NEON_PROJECT_ID", ""),
        help="Neon project id (default: $NEON_PROJECT_ID)",
    )
    parser.add_argument(
        "--parent",
        default=os.environ.get("NEON_PARENT_BRANCH") or "production",
        help="Neon branch to copy (default: $NEON_PARENT_BRANCH or production)",
    )
    parser.add_argument(
        "pytest_args", nargs="*", help="extra pytest arguments, after `--`"
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    targets = [args.only] if args.only else [POSTGRES, R2]
    env = dict(os.environ)

    if POSTGRES in targets and not args.project_id:
        sys.exit("NEON_PROJECT_ID is unset (or pass --project-id).")
    if R2 in targets:
        missing = [name for name in R2_TEST_VARS if not env.get(name)]
        if missing:
            sys.exit(f"missing R2 variables: {', '.join(missing)}")

    run_id = new_run_id()
    branch = f"local-{run_id}"
    branch_created = False
    if R2 in targets:
        env["R2_TEST_PREFIX"] = r2_prefix(run_id)

    try:
        if POSTGRES in targets:
            print(f"creating Neon branch {branch} off {args.parent}")
            dsn = create_branch(args.project_id, args.parent, branch)
            branch_created = True
            env["POSTGRES_TEST_URL"] = dsn
            migrate_env = {
                **env,
                "DATABASE_URL": dsn,
                "DATABASE_URL_UNPOOLED": dsn,
            }
            print("applying migrations to the branch")
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                check=True,
                env=migrate_env,
            )
        else:
            env.pop("POSTGRES_TEST_URL", None)

        pytest = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-m",
                marker_expression(targets),
                *args.pytest_args,
            ],
            env=env,
        )
        return pytest.returncode
    finally:
        if R2 in targets:
            subprocess.run(
                [sys.executable, "-m", "scripts.ci_r2_cleanup"],
                env=env,
                check=False,
            )
        if branch_created and not args.keep_branch:
            delete_branch(args.project_id, branch)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
