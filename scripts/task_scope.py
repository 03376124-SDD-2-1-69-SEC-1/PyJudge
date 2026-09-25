"""Read docs/task-scope.md and say which tasks `/start-task` may offer.

    uv run python -m scripts.task_scope <owner> [--maintainer]

The Status column is the only source of truth: `open`, `in-progress` or
`done`. A branch existing or not never decides it. Rows whose ID ends in `-*`
(OPS-*, BUG-*) are patterns, not tasks: they skip the Status check and are
never offered.

A friend is offered:

- `open` rows owned by them, or by `TBD` (nobody yet, anyone may take it);
- `in-progress` rows owned by them.

A row is stale when a path in its "May touch" cell is missing from the repo,
or its text uses a term from the retired two-service design. Stale rows are
hidden from friends and listed under "needs updating" for the maintainer
(พาย, or anyone passing `--maintainer`). A path that the task itself has to
create goes in its own `creates:` segment, and is not counted as missing:

    `core/a/`; creates: `core/b/`, `core/b/service.py`
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASK_SCOPE = ROOT / "docs" / "task-scope.md"

VALID_STATUSES = ("open", "in-progress", "done")
MAINTAINER = "พาย"
UNOWNED = "TBD"
REQUIRED_COLUMNS = ("TASK-ID", "Owner", "Status", "May touch", "Done when")

# Terms from the two-service design that ADR-0007 retired. HTTP is matched
# case-sensitively so the `http-equiv` attribute of a <meta> tag is not caught.
STALE_TERMS = (
    re.compile(r"ai repo", re.IGNORECASE),
    re.compile(r"2 service", re.IGNORECASE),
    re.compile(r"two service", re.IGNORECASE),
    re.compile(r"AI/RAG Service", re.IGNORECASE),
    re.compile(r"\bHTTP\b"),
    re.compile(r"mirror", re.IGNORECASE),
)

_CELL_SPLIT = re.compile(r"(?<!\\)\|")
_TICKS = re.compile(r"`([^`]+)`")


class TaskScopeError(Exception):
    """task-scope.md cannot be read as a task table."""


@dataclass(frozen=True, slots=True)
class Row:
    """One row of the task table."""

    task_id: str
    owner: str
    status: str
    may_touch: str
    done_when: str

    @property
    def is_pattern(self) -> bool:
        """OPS-* and BUG-*: a family of tasks, not one task."""
        return self.task_id.endswith("-*")

    @property
    def owners(self) -> tuple[str, ...]:
        """Owner names; `A + B` is a shared row."""
        return tuple(name.strip() for name in self.owner.split("+"))

    @property
    def unowned(self) -> bool:
        """No owner yet, so anyone may take it."""
        return self.owners == (UNOWNED,)

    @property
    def existing_paths(self) -> tuple[str, ...]:
        """Paths the task edits, which must already be in the repo."""
        return tuple(
            path
            for segment in self.may_touch.split(";")
            if not _is_creates(segment)
            for path in _TICKS.findall(segment)
        )

    @property
    def creates_paths(self) -> tuple[str, ...]:
        """Paths the task creates itself."""
        return tuple(
            path
            for segment in self.may_touch.split(";")
            if _is_creates(segment)
            for path in _TICKS.findall(segment)
        )


@dataclass(frozen=True, slots=True)
class Listing:
    """What one person is shown."""

    offered: tuple[Row, ...]
    needs_updating: tuple[tuple[Row, tuple[str, ...]], ...]


def _is_creates(segment: str) -> bool:
    return segment.strip().startswith("creates:")


def _cells(line: str) -> list[str]:
    inner = line.strip().removeprefix("|").removesuffix("|")
    return [cell.strip() for cell in _CELL_SPLIT.split(inner)]


def parse_rows(text: str) -> list[Row]:
    """Read the task table; raise TaskScopeError naming what is wrong."""
    lines = text.splitlines()
    header_at = next(
        (i for i, line in enumerate(lines) if line.lstrip().startswith("| TASK-ID")),
        -1,
    )
    if header_at == -1:
        raise TaskScopeError("no table with a TASK-ID column")
    header = _cells(lines[header_at])
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        raise TaskScopeError(f"the table has no {', '.join(missing)} column")
    index = {name: header.index(name) for name in REQUIRED_COLUMNS}

    rows: list[Row] = []
    for line in lines[header_at + 2 :]:
        if not line.lstrip().startswith("|"):
            break
        cells = _cells(line)
        task_id = cells[0]
        if len(cells) != len(header):
            raise TaskScopeError(
                f"{task_id}: {len(cells)} cells, the header has {len(header)}"
            )
        row = Row(**{_FIELDS[name]: cells[index[name]] for name in REQUIRED_COLUMNS})
        _check_status(row)
        rows.append(row)

    seen: set[str] = set()
    for row in rows:
        if row.task_id in seen:
            raise TaskScopeError(f"{row.task_id}: listed twice")
        seen.add(row.task_id)
    return rows


_FIELDS = {
    "TASK-ID": "task_id",
    "Owner": "owner",
    "Status": "status",
    "May touch": "may_touch",
    "Done when": "done_when",
}


def _check_status(row: Row) -> None:
    if row.is_pattern:
        return
    if not row.status:
        raise TaskScopeError(f"{row.task_id}: no Status")
    if row.status not in VALID_STATUSES:
        raise TaskScopeError(
            f"{row.task_id}: unknown Status {row.status!r}, "
            f"expected one of {', '.join(VALID_STATUSES)}"
        )


def _path_exists(root: Path, path: str) -> bool:
    for base in (root, root / "src" / "greader"):
        if "*" in path:
            if any(base.glob(path)):
                return True
        elif (base / path).exists():
            return True
    return False


def stale_reasons(row: Row, root: Path = ROOT) -> tuple[str, ...]:
    """Why this row no longer matches the tree; empty when it is current."""
    reasons = [
        f"path not in repo: {path}"
        for path in row.existing_paths
        if not _path_exists(root, path)
    ]
    text = " ".join((row.owner, row.may_touch, row.done_when))
    reasons += [
        f"retired wording: {match.group(0)!r}"
        for term in STALE_TERMS
        if (match := term.search(text))
    ]
    return tuple(reasons)


def list_tasks(
    rows: list[Row], owner: str, *, maintainer: bool = False, root: Path = ROOT
) -> Listing:
    """Rows `owner` may start, and (for the maintainer) rows needing an update."""
    if not owner.strip():
        raise TaskScopeError("owner is empty")
    owner = owner.strip()
    maintainer = maintainer or owner == MAINTAINER

    offered: list[Row] = []
    needs_updating: list[tuple[Row, tuple[str, ...]]] = []
    for row in rows:
        if row.is_pattern or row.status == "done":
            continue
        mine = owner in row.owners
        wanted = mine or (row.status == "open" and row.unowned)
        reasons = stale_reasons(row, root)
        if reasons:
            if maintainer:
                needs_updating.append((row, reasons))
        elif wanted:
            offered.append(row)
    return Listing(tuple(offered), tuple(needs_updating))


def render(listing: Listing, owner: str, *, maintainer: bool) -> str:
    """Text shown by `/start-task`."""
    lines: list[str] = []
    if not listing.offered:
        lines.append(f"No tasks for {owner}.")
    for number, row in enumerate(listing.offered, start=1):
        tag = "ยังไม่มีเจ้าของ รับได้" if row.unowned else row.status
        lines.append(f"{number}. {row.task_id} [{tag}]")
        lines.append(f"   May touch: {row.may_touch}")
        lines.append(f"   Done when: {row.done_when}")
    if maintainer and listing.needs_updating:
        lines.append("")
        lines.append("งานที่ต้องอัปเดต (ซ่อนจากเพื่อน):")
        for row, reasons in listing.needs_updating:
            lines.append(f"- {row.task_id} [{row.status}]: {'; '.join(reasons)}")
    return "\n".join(lines)


def main(
    argv: list[str] | None = None, *, path: Path = TASK_SCOPE, root: Path = ROOT
) -> int:
    """CLI entry point; a table that cannot be read exits with 1."""
    parser = argparse.ArgumentParser(prog="task_scope")
    parser.add_argument("owner")
    parser.add_argument("--maintainer", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = parse_rows(path.read_text(encoding="utf-8"))
        listing = list_tasks(rows, args.owner, maintainer=args.maintainer, root=root)
    except TaskScopeError as error:
        print(f"task-scope.md: {error}", file=sys.stderr)
        return 1
    maintainer = args.maintainer or args.owner.strip() == MAINTAINER
    print(render(listing, args.owner, maintainer=maintainer))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
