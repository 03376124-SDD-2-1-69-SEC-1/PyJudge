"""In-memory SubmissionRepository and two CodeRunners for tests and the demo."""

import contextlib
import math
import os
import resource
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import replace

from greader.core.submissions.models import Execution, ExecutionStatus, Submission


class FakeSubmissionRepository:
    def __init__(self) -> None:
        self._rows: list[Submission] = []

    def add(self, submission: Submission) -> Submission:
        saved = replace(submission, id=len(self._rows) + 1)
        self._rows.append(saved)
        return saved

    def get(self, submission_id: int) -> Submission | None:
        return next((row for row in self._rows if row.id == submission_id), None)

    def list_for_student(
        self, posting_id: int, student_id: int
    ) -> tuple[Submission, ...]:
        return tuple(
            row
            for row in self._ordered()
            if row.posting_id == posting_id and row.student_id == student_id
        )

    def list_for_posting(self, posting_id: int) -> tuple[Submission, ...]:
        return tuple(row for row in self._ordered() if row.posting_id == posting_id)

    def _ordered(self) -> list[Submission]:
        return sorted(self._rows, key=lambda row: (row.submitted_at, row.id))


class ScriptedCodeRunner:
    """Answers from `outputs` (stdin -> stdout); code markers force failures.

    A line `# tle` in the code times out and `# crash` raises a runtime
    error, so a test can reach S-02d without running anything.
    """

    def __init__(self, outputs: dict[str, str] | None = None) -> None:
        self.outputs: dict[str, str] = {}
        if outputs is not None:
            self.outputs.update(outputs)
        self.calls: list[str] = []

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution:
        self.calls.append(stdin)
        if "# tle" in code:
            return Execution(ExecutionStatus.TIME_LIMIT, "", "", time_limit_seconds)
        if "# crash" in code:
            return Execution(
                ExecutionStatus.RUNTIME_ERROR,
                "",
                "IndexError: list index out of range",
                0.01,
            )
        return Execution(ExecutionStatus.OK, self.outputs.get(stdin, ""), "", 0.02)


class UnsafeRunnerInProductionError(RuntimeError):
    """LocalUnsafeRunner was built with ENV=production."""


class LocalUnsafeRunner:
    """Demo only: runs code with this machine's Python, NOT a sandbox.

    Guards, none of which make it safe for untrusted code: it refuses to
    exist when ENV=production, each run gets a fresh temp dir as its working
    directory, a wall-clock timeout, and CPU-time and memory rlimits (POSIX).
    `scripts/demo.py` binds 127.0.0.1, so the only code it runs is what the
    person at the keyboard typed. Production needs a sandboxed CodeRunner
    (ADR-0007 open question 1).
    """

    MEMORY_BYTES = 256 * 1024 * 1024

    def __init__(self) -> None:
        if os.environ.get("ENV", "").strip().lower() == "production":
            raise UnsafeRunnerInProductionError(
                "LocalUnsafeRunner runs code unsandboxed; refusing ENV=production"
            )

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="greader-run-") as workdir:
            try:
                done = subprocess.run(
                    [sys.executable, "-I", "-c", code],
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=time_limit_seconds,
                    check=False,
                    cwd=workdir,
                    env={"PATH": os.environ.get("PATH", "")},
                    preexec_fn=self._limits(time_limit_seconds),
                )
            except subprocess.TimeoutExpired:
                return Execution(ExecutionStatus.TIME_LIMIT, "", "", time_limit_seconds)
        elapsed = time.perf_counter() - started
        if done.returncode != 0:
            return Execution(
                ExecutionStatus.RUNTIME_ERROR, done.stdout, done.stderr, elapsed
            )
        return Execution(ExecutionStatus.OK, done.stdout, done.stderr, elapsed)

    def _limits(self, time_limit_seconds: float) -> Callable[[], None]:
        cpu_seconds = math.ceil(time_limit_seconds) + 1

        def apply() -> None:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            # macOS rejects RLIMIT_AS; the CPU limit and timeout still hold.
            with contextlib.suppress(ValueError, OSError):
                resource.setrlimit(
                    resource.RLIMIT_AS, (self.MEMORY_BYTES, self.MEMORY_BYTES)
                )

        return apply
