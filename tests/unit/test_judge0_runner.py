"""Judge0CodeRunner against a scripted Judge0 CE behind httpx.MockTransport."""

import base64
import json
from collections.abc import Callable
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from questly.core.assignments.models import Language
from questly.core.submissions.models import (
    Execution,
    ExecutionStatus,
    RunnerUnavailableError,
    UnsupportedLanguageError,
)
from questly.integrations.judge0 import (
    JUDGE0_LANGUAGE_IDS,
    Judge0CodeRunner,
    StubCodeRunner,
)
from questly.main import build_code_runner
from tests.fakes.app import fake_settings

BASE = "http://judge0.test"


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _unb64(text: str) -> str:
    return base64.b64decode(text).decode()


def _done(
    status_id: int,
    stdout: str = "",
    *,
    stderr: str | None = None,
    compile_output: str | None = None,
    time: str | None = "0.012",
) -> dict[str, object]:
    return {
        "status_id": status_id,
        "stdout": _b64(stdout) if stdout else None,
        "stderr": _b64(stderr) if stderr is not None else None,
        "compile_output": _b64(compile_output) if compile_output is not None else None,
        "time": time,
    }


class FakeJudge0:
    """Hands out tokens t0, t1, ... and answers each poll from a script.

    `polls` is one list per GET: the reply for every token asked about, in
    order of creation, minus the token field. When the script runs out the
    last poll repeats.
    """

    def __init__(self, polls: list[list[dict[str, object]]]) -> None:
        self.polls = polls
        self.created: list[dict[str, object]] = []
        self.requests: list[httpx.Request] = []
        self.gets = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.url.path == "/submissions/batch"
        assert parse_qs(request.url.query.decode())["base64_encoded"] == ["true"]
        if request.method == "POST":
            body = json.loads(request.content)
            start = len(self.created)
            self.created.extend(body["submissions"])
            return httpx.Response(
                201,
                json=[
                    {"token": f"t{start + n}"} for n in range(len(body["submissions"]))
                ],
            )
        query = parse_qs(urlsplit(str(request.url)).query)
        tokens = query["tokens"][0].split(",")
        fields = set(query["fields"][0].split(","))
        assert {"token", "status_id", "stdout", "stderr", "time"} <= fields
        assert "expected_output" not in fields
        replies = self.polls[min(self.gets, len(self.polls) - 1)]
        self.gets += 1
        return httpx.Response(
            200,
            json={
                "submissions": [
                    {"token": token, **replies[int(token[1:])]} for token in tokens
                ]
            },
        )


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _runner(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    auth_token: str = "",
    time: FakeTime | None = None,
) -> Judge0CodeRunner:
    if time is None:
        time = FakeTime()
    return Judge0CodeRunner(
        base_url=BASE,
        auth_token=auth_token,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        poll_interval_seconds=0.5,
        timeout_seconds=5.0,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


def _run_many(runner: Judge0CodeRunner, stdins: list[str]) -> tuple[Execution, ...]:
    return runner.run_many(
        code="print(input())",
        language="python3",
        stdins=stdins,
        time_limit_seconds=1.5,
    )


def test_one_batch_sends_base64_code_and_inputs_and_never_expected_output() -> None:
    judge0 = FakeJudge0([[_done(3, "a\n"), _done(3, "b\n")]])

    _run_many(_runner(judge0, auth_token="secret"), ["a", "b"])

    posts = [r for r in judge0.requests if r.method == "POST"]
    assert len(posts) == 1
    assert [_unb64(str(s["stdin"])) for s in judge0.created] == ["a", "b"]
    for sent in judge0.created:
        assert _unb64(str(sent["source_code"])) == "print(input())"
        assert sent["language_id"] == 71
        assert sent["cpu_time_limit"] == 1.5
        assert "expected_output" not in sent
    assert all(r.headers["X-Auth-Token"] == "secret" for r in judge0.requests)


def test_no_auth_header_without_a_token() -> None:
    judge0 = FakeJudge0([[_done(3, "a")]])

    _run_many(_runner(judge0), ["a"])

    assert all("X-Auth-Token" not in r.headers for r in judge0.requests)


def test_polls_until_nothing_is_queued_or_processing() -> None:
    queued = {"status_id": 1, "stdout": None, "stderr": None, "time": None}
    processing = {"status_id": 2, "stdout": None, "stderr": None, "time": None}
    judge0 = FakeJudge0(
        [[queued, queued], [_done(3, "1"), processing], [_done(3, "1"), _done(3, "2")]]
    )
    time = FakeTime()

    executions = _run_many(_runner(judge0, time=time), ["x", "y"])

    assert judge0.gets == 3 and time.slept == [0.5, 0.5]
    assert [e.stdout for e in executions] == ["1", "2"]


def test_results_come_back_in_input_order_with_decoded_output() -> None:
    judge0 = FakeJudge0([[_done(3, "first\n", time="0.25"), _done(3, "second\n")]])

    executions = _run_many(_runner(judge0), ["1", "2"])

    assert executions == (
        Execution(ExecutionStatus.OK, "first\n", "", 0.25),
        Execution(ExecutionStatus.OK, "second\n", "", 0.012),
    )


def test_judge0_wrong_answer_is_not_trusted_the_service_compares_output() -> None:
    judge0 = FakeJudge0([[_done(4, "42")]])

    (execution,) = _run_many(_runner(judge0), ["x"])

    assert execution == Execution(ExecutionStatus.OK, "42", "", 0.012)


@pytest.mark.parametrize(
    ("status_id", "expected"),
    [
        (5, ExecutionStatus.TIME_LIMIT),
        (6, ExecutionStatus.RUNTIME_ERROR),
        *((n, ExecutionStatus.RUNTIME_ERROR) for n in range(7, 13)),
        (14, ExecutionStatus.RUNTIME_ERROR),
    ],
)
def test_finished_statuses_map_onto_execution_status(
    status_id: int, expected: ExecutionStatus
) -> None:
    judge0 = FakeJudge0([[_done(status_id, stderr="boom", time=None)]])

    (execution,) = _run_many(_runner(judge0), ["x"])

    assert execution.status is expected
    assert execution.stderr == "boom" and execution.time_seconds == 0.0


def test_a_compilation_error_reports_the_compiler_output() -> None:
    judge0 = FakeJudge0([[_done(6, compile_output="SyntaxError: bad")]])

    (execution,) = _run_many(_runner(judge0), ["x"])

    assert execution.status is ExecutionStatus.RUNTIME_ERROR
    assert execution.stderr == "SyntaxError: bad"


def test_an_internal_error_means_the_runner_is_unavailable() -> None:
    judge0 = FakeJudge0([[_done(3, "ok"), _done(13)]])

    with pytest.raises(RunnerUnavailableError):
        _run_many(_runner(judge0), ["x", "y"])


def test_a_judge_still_queued_at_the_deadline_is_unavailable() -> None:
    queued = {"status_id": 1, "stdout": None, "stderr": None, "time": None}
    judge0 = FakeJudge0([[queued]])
    time = FakeTime()

    with pytest.raises(RunnerUnavailableError):
        _run_many(_runner(judge0, time=time), ["x"])

    assert time.now <= 5.0 and judge0.gets == len(time.slept) + 1


def test_a_connection_error_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(RunnerUnavailableError):
        _run_many(_runner(refuse), ["x"])


@pytest.mark.parametrize("status_code", [401, 422, 500, 503])
def test_a_non_2xx_reply_is_unavailable(status_code: int) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "nope"})

    with pytest.raises(RunnerUnavailableError):
        _run_many(_runner(fail), ["x"])


def test_a_rejected_batch_item_is_unavailable() -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json=[{"language_id": ["doesn't exist"]}])

    with pytest.raises(RunnerUnavailableError):
        _run_many(_runner(reject), ["x"])


def test_an_unknown_language_is_a_domain_error_before_any_request() -> None:
    judge0 = FakeJudge0([[_done(3)]])

    with pytest.raises(UnsupportedLanguageError):
        _runner(judge0).run_many(
            code="", language="cobol", stdins=["x"], time_limit_seconds=1
        )

    assert judge0.requests == []


def test_every_domain_language_has_a_judge0_id() -> None:
    assert set(JUDGE0_LANGUAGE_IDS) == set(Language)


def test_an_empty_batch_makes_no_request() -> None:
    judge0 = FakeJudge0([[_done(3)]])

    assert _run_many(_runner(judge0), []) == ()
    assert judge0.requests == []


def test_more_inputs_than_one_judge0_batch_holds_are_split_in_order() -> None:
    stdins = [str(n) for n in range(45)]
    judge0 = FakeJudge0([[_done(3, n) for n in stdins]])

    executions = _run_many(_runner(judge0), stdins)

    posts = [r for r in judge0.requests if r.method == "POST"]
    assert [len(json.loads(p.content)["submissions"]) for p in posts] == [20, 20, 5]
    assert [e.stdout for e in executions] == stdins


def test_run_is_a_batch_of_one() -> None:
    judge0 = FakeJudge0([[_done(3, "7")]])

    execution = _runner(judge0).run(
        code="print(7)", language="python3", stdin="", time_limit_seconds=1
    )

    assert execution.stdout == "7"
    assert [r.method for r in judge0.requests] == ["POST", "GET"]


def test_the_app_runs_code_on_judge0_only_when_a_url_is_configured() -> None:
    off = fake_settings()
    on = replace(off, judge0_url="http://judge0:2358", judge0_auth_token="t")

    assert isinstance(build_code_runner(off), StubCodeRunner)
    assert isinstance(build_code_runner(on), Judge0CodeRunner)
