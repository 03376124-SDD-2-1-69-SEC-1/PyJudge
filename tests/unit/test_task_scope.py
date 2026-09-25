"""`/start-task` offers a task only when Status, owner and paths agree."""

from pathlib import Path

import pytest
from scripts.task_scope import (
    ROOT,
    TASK_SCOPE,
    Row,
    TaskScopeError,
    list_tasks,
    main,
    parse_rows,
    render,
    stale_reasons,
)

HEADER = "| TASK-ID | Owner | Status | May touch | Done when |\n|---|---|---|---|---|\n"


def table(*rows: str) -> str:
    return "Intro text.\n\n" + HEADER + "\n".join(rows) + "\n\nAfter the table.\n"


def ids(listing_rows: tuple[Row, ...]) -> list[str]:
    return [row.task_id for row in listing_rows]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "src" / "greader" / "core" / "topics").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    return tmp_path


def offered(
    text: str, owner: str, repo: Path, *, maintainer: bool = False
) -> list[str]:
    listing = list_tasks(parse_rows(text), owner, maintainer=maintainer, root=repo)
    return ids(listing.offered)


def test_open_task_of_the_runner_is_offered(repo: Path) -> None:
    text = table("| A-1 | นัด | open | `core/topics/` | done |")

    assert offered(text, "นัด", repo) == ["A-1"]


def test_open_task_without_an_owner_is_offered_to_anyone(repo: Path) -> None:
    text = table("| A-1 | TBD | open | `core/topics/` | done |")

    listing = list_tasks(parse_rows(text), "นัด", root=repo)

    assert ids(listing.offered) == ["A-1"]
    assert "ยังไม่มีเจ้าของ รับได้" in render(listing, "นัด", maintainer=False)


def test_open_task_of_someone_else_is_hidden(repo: Path) -> None:
    text = table("| A-1 | ฟิล์ม | open | `core/topics/` | done |")

    assert offered(text, "นัด", repo) == []


def test_in_progress_task_is_offered_only_to_its_owner(repo: Path) -> None:
    text = table(
        "| A-1 | นัด | in-progress | `core/topics/` | done |",
        "| A-2 | TBD | in-progress | `core/topics/` | done |",
    )

    assert offered(text, "นัด", repo) == ["A-1"]
    assert offered(text, "ฟิล์ม", repo) == []


def test_done_task_is_never_offered(repo: Path) -> None:
    text = table("| A-1 | นัด | done | `core/topics/` | done |")

    assert offered(text, "นัด", repo) == []


def test_shared_row_is_offered_to_each_owner(repo: Path) -> None:
    text = table("| A-1 | พาย + ฟิล์ม | open | `core/topics/` | done |")

    assert offered(text, "ฟิล์ม", repo) == ["A-1"]
    assert offered(text, "นัด", repo) == []


def test_pattern_rows_are_never_offered_and_skip_the_status_check(repo: Path) -> None:
    text = table("| OPS-* | พาย | — | anything | varies |")

    assert offered(text, "พาย", repo) == []


def test_missing_path_hides_the_task_from_friends(repo: Path) -> None:
    text = table("| A-1 | นัด | open | `core/gone/` | done |")

    assert offered(text, "นัด", repo) == []


def test_missing_path_is_listed_for_the_maintainer(repo: Path) -> None:
    text = table("| A-1 | นัด | open | `core/gone/` | done |")

    listing = list_tasks(parse_rows(text), "พาย", root=repo)

    assert [row.task_id for row, _ in listing.needs_updating] == ["A-1"]
    assert "path not in repo: core/gone/" in render(listing, "พาย", maintainer=True)


def test_maintainer_flag_shows_the_update_list_to_anyone(repo: Path) -> None:
    text = table("| A-1 | ฟิล์ม | open | `core/gone/` | done |")

    friend = list_tasks(parse_rows(text), "นัด", root=repo)
    flagged = list_tasks(parse_rows(text), "นัด", maintainer=True, root=repo)

    assert friend.needs_updating == ()
    assert [row.task_id for row, _ in flagged.needs_updating] == ["A-1"]


def test_path_the_task_creates_is_not_stale(repo: Path) -> None:
    text = table("| A-1 | นัด | open | `core/topics/`; creates: `core/new/` | done |")

    assert offered(text, "นัด", repo) == ["A-1"]


def test_creates_does_not_excuse_a_missing_existing_path(repo: Path) -> None:
    text = table("| A-1 | นัด | open | `core/gone/`; creates: `core/new/` | done |")

    assert offered(text, "นัด", repo) == []


def test_path_under_src_greader_or_the_repo_root_counts(repo: Path) -> None:
    (repo / "docs" / "note.md").write_text("x", encoding="utf-8")
    text = table("| A-1 | นัด | open | `core/topics/`, `docs/note.md` | done |")

    assert offered(text, "นัด", repo) == ["A-1"]


def test_glob_path_needs_a_match(repo: Path) -> None:
    (repo / "src" / "greader" / "web").mkdir()
    (repo / "src" / "greader" / "web" / "g01.html").write_text("x", encoding="utf-8")
    text = table(
        "| A-1 | นัด | open | `web/g*` | done |",
        "| A-2 | นัด | open | `web/z*` | done |",
    )

    assert offered(text, "นัด", repo) == ["A-1"]


@pytest.mark.parametrize(
    "wording",
    [
        "runs in the ai repo",
        "the AI/RAG Service",
        "two service split",
        "2 service split",
        "calls over HTTP",
        "mirror the rows",
    ],
)
def test_retired_wording_hides_the_task(repo: Path, wording: str) -> None:
    text = table(f"| A-1 | นัด | open | `core/topics/` | {wording} |")

    assert offered(text, "นัด", repo) == []
    assert stale_reasons(parse_rows(text)[0], repo)


def test_meta_http_equiv_is_not_retired_wording(repo: Path) -> None:
    text = table('| A-1 | นัด | open | `core/topics/` | `<meta http-equiv="refresh">` |')

    assert offered(text, "นัด", repo) == ["A-1"]


@pytest.mark.parametrize("status", ["todo", "Open", "wip", "closed"])
def test_unknown_status_fails_naming_the_row(status: str) -> None:
    text = table(f"| A-9 | นัด | {status} | `core/topics/` | done |")

    with pytest.raises(TaskScopeError, match=r"A-9: unknown Status"):
        parse_rows(text)


def test_empty_status_fails_naming_the_row() -> None:
    text = table("| A-9 | นัด |  | `core/topics/` | done |")

    with pytest.raises(TaskScopeError, match=r"A-9: no Status"):
        parse_rows(text)


def test_table_without_a_status_column_fails() -> None:
    text = (
        "| TASK-ID | Owner | May touch | Done when |\n|---|---|---|---|\n"
        "| A-1 | นัด | `x` | y |\n"
    )

    with pytest.raises(TaskScopeError, match="no Status column"):
        parse_rows(text)


def test_row_with_the_wrong_cell_count_fails_naming_the_row() -> None:
    text = table("| A-9 | นัด | open | `core/topics/` |")

    with pytest.raises(TaskScopeError, match=r"A-9: 4 cells"):
        parse_rows(text)


def test_duplicate_task_id_fails() -> None:
    text = table(
        "| A-1 | นัด | open | `x` | y |",
        "| A-1 | นัด | open | `x` | y |",
    )

    with pytest.raises(TaskScopeError, match=r"A-1: listed twice"):
        parse_rows(text)


def test_cli_prints_the_list(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    scope = repo / "docs" / "task-scope.md"
    scope.write_text(
        table("| A-1 | นัด | open | `core/topics/` | ship it |"), encoding="utf-8"
    )

    code = main(["นัด"], path=scope, root=repo)

    assert code == 0
    assert "1. A-1 [open]" in capsys.readouterr().out


def test_cli_fails_on_an_unknown_status(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scope = repo / "docs" / "task-scope.md"
    scope.write_text(table("| A-9 | นัด | wip | `x` | y |"), encoding="utf-8")

    code = main(["นัด"], path=scope, root=repo)

    assert code == 1
    assert "A-9" in capsys.readouterr().err


def test_empty_owner_is_refused() -> None:
    with pytest.raises(TaskScopeError, match="owner is empty"):
        list_tasks(parse_rows(table("| A-1 | นัด | open | `x` | y |")), " ")


# The real table ---------------------------------------------------------------


def test_the_real_table_has_a_valid_status_on_every_task() -> None:
    rows = parse_rows(TASK_SCOPE.read_text(encoding="utf-8"))

    assert rows
    assert all(row.is_pattern or row.status for row in rows)


def test_no_open_or_in_progress_task_in_the_real_table_is_stale() -> None:
    rows = parse_rows(TASK_SCOPE.read_text(encoding="utf-8"))

    listing = list_tasks(rows, "พาย", maintainer=True, root=ROOT)

    assert [(row.task_id, reasons) for row, reasons in listing.needs_updating] == []
