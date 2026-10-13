"""CodeRunner adapters. Judge0 CE comes later; the stub runs nothing."""

import logging
from collections.abc import Sequence

from questly.core.submissions.models import Execution, ExecutionStatus

logger = logging.getLogger("questly.judge0")


class StubCodeRunner:
    """Satisfies CodeRunner without Judge0: every run is a runtime error.

    Records each call so a deployment without Judge0 fails visibly instead
    of grading code it never ran.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def run(
        self, *, code: str, language: str, stdin: str, time_limit_seconds: float
    ) -> Execution:
        self.calls.append((language, stdin))
        logger.warning("code runner not configured; %s run refused", language)
        return Execution(
            status=ExecutionStatus.RUNTIME_ERROR,
            stdout="",
            stderr="The code runner is not configured.",
            time_seconds=0.0,
        )

    def run_many(
        self,
        *,
        code: str,
        language: str,
        stdins: Sequence[str],
        time_limit_seconds: float,
    ) -> tuple[Execution, ...]:
        return tuple(
            self.run(
                code=code,
                language=language,
                stdin=stdin,
                time_limit_seconds=time_limit_seconds,
            )
            for stdin in stdins
        )
