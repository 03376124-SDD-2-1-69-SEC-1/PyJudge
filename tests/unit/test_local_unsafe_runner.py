"""The demo's LocalUnsafeRunner: its guards, not its safety (it has none)."""

import pytest

from greader.core.submissions.models import ExecutionStatus
from tests.fakes.submissions import LocalUnsafeRunner, UnsafeRunnerInProductionError


def test_refuses_to_exist_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "production")

    with pytest.raises(UnsafeRunnerInProductionError):
        LocalUnsafeRunner()


def test_runs_in_a_temp_dir_with_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    code = "import os\nprint(input()[::-1], os.path.basename(os.getcwd())[:12])"

    result = LocalUnsafeRunner().run(
        code=code, language="python3", stdin="abc", time_limit_seconds=5
    )

    assert result.status is ExecutionStatus.OK
    assert result.stdout.split() == ["cba", "greader-run-"]


def test_times_out_and_reports_crashes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
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
