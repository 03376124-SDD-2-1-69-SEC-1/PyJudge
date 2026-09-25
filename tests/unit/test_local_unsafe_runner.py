"""The demo's LocalUnsafeRunner: its guards, not its safety (it has none)."""

import pytest

from greader.core.submissions.models import ExecutionStatus
from tests.fakes.submissions import LocalUnsafeRunner, UnsafeRunnerNotAllowedError


def test_refuses_without_the_explicit_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENV unset (as on a misconfigured server) must fail closed."""
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("ALLOW_UNSAFE_RUNNER", raising=False)

    with pytest.raises(UnsafeRunnerNotAllowedError, match="ALLOW_UNSAFE_RUNNER"):
        LocalUnsafeRunner()


@pytest.mark.parametrize("flag", ["0", "true", "yes", ""])
def test_only_the_value_1_opts_in(monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("ALLOW_UNSAFE_RUNNER", flag)

    with pytest.raises(UnsafeRunnerNotAllowedError):
        LocalUnsafeRunner()


def test_production_refuses_even_with_the_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ALLOW_UNSAFE_RUNNER", "1")

    with pytest.raises(UnsafeRunnerNotAllowedError, match="production"):
        LocalUnsafeRunner()


def test_runs_in_a_temp_dir_with_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("ALLOW_UNSAFE_RUNNER", "1")
    code = "import os\nprint(input()[::-1], os.path.basename(os.getcwd())[:12])"

    result = LocalUnsafeRunner().run(
        code=code, language="python3", stdin="abc", time_limit_seconds=5
    )

    assert result.status is ExecutionStatus.OK
    assert result.stdout.split() == ["cba", "greader-run-"]


def test_times_out_and_reports_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("ALLOW_UNSAFE_RUNNER", "1")
    runner = LocalUnsafeRunner()

    looping = runner.run(
        code="while True: pass", language="python3", stdin="", time_limit_seconds=0.5
    )
    crashing = runner.run(
        code="[][1]", language="python3", stdin="", time_limit_seconds=5
    )

    assert looping.status is ExecutionStatus.TIME_LIMIT
    assert crashing.status is ExecutionStatus.RUNTIME_ERROR
    assert "IndexError" in crashing.stderr
