"""G-02a: how stored notifications and due-soon items become dropdown rows."""

from datetime import UTC, datetime, timedelta

import pytest

from questly.core.notifications.menu import (
    MENU_SIZE,
    build_menu,
    describe,
)
from questly.core.notifications.models import (
    DueSoon,
    Notification,
    NotificationKind,
    NotificationPayload,
)
from questly.core.notifications.pages import local_path

NOW = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)


def stored(
    kind: NotificationKind,
    *,
    id: int = 1,
    read: bool = False,
    reason: str | None = None,
    age: timedelta = timedelta(hours=1),
) -> Notification:
    payload: NotificationPayload = {
        "classroom_id": 7,
        "assignment_id": 3,
        "title": "Binary search",
    }
    if reason is not None:
        payload["reason"] = reason
    return Notification(
        id=id,
        user_id=1,
        kind=kind,
        payload=payload,
        created_at=NOW - age,
        read_at=NOW if read else None,
    )


def test_a_published_notification_names_the_new_problem_and_links_to_it() -> None:
    row = describe(stored(NotificationKind.ASSIGNMENT_PUBLISHED))

    assert row.title == "New problem: Binary search"
    assert row.detail == ""
    assert row.href == "/classes/7/assignments/3"
    assert row.unread is True


def test_an_updated_notification_carries_the_instructors_reason() -> None:
    row = describe(stored(NotificationKind.ASSIGNMENT_UPDATED, reason="Fixed sample 2"))

    assert row.title == "Problem updated: Binary search"
    assert row.detail == "Fixed sample 2"


def test_an_updated_notification_without_a_reason_has_no_detail() -> None:
    assert describe(stored(NotificationKind.ASSIGNMENT_UPDATED)).detail == ""


def test_a_notified_notification_is_a_reminder() -> None:
    row = describe(stored(NotificationKind.ASSIGNMENT_NOTIFIED, read=True))

    assert row.title == "Reminder: Binary search"
    assert row.unread is False


def test_the_menu_counts_every_unread_notification_but_lists_only_the_latest() -> None:
    notifications = [
        stored(NotificationKind.ASSIGNMENT_PUBLISHED, id=n, read=n > MENU_SIZE + 2)
        for n in range(1, MENU_SIZE + 5)
    ]

    menu = build_menu(notifications, [])

    assert len(menu.recent) == MENU_SIZE
    assert [row.id for row in menu.recent] == list(range(1, MENU_SIZE + 1))
    assert menu.unread_count == MENU_SIZE + 2


def test_due_soon_rows_say_deadline_tomorrow_and_link_to_the_problem() -> None:
    deadline = NOW + timedelta(hours=5)
    menu = build_menu(
        [],
        [DueSoon(classroom_id=7, assignment_id=3, title="Sorting", deadline=deadline)],
    )

    (row,) = menu.due_soon
    assert row.title == "Deadline tomorrow: Sorting"
    assert row.href == "/classes/7/assignments/3"
    assert row.deadline == deadline
    assert menu.unread_count == 0
    assert menu.is_empty is False


def test_an_empty_menu_is_empty_and_a_menu_with_either_list_is_not() -> None:
    assert build_menu([], []).is_empty is True
    assert (
        build_menu([stored(NotificationKind.ASSIGNMENT_PUBLISHED)], []).is_empty
        is False
    )


@pytest.mark.parametrize(
    "target",
    ["/", "/classes", "/classes/7?tab=members", "/classes/7/assignments/3?tab=history"],
)
def test_local_paths_are_kept(target: str) -> None:
    assert local_path(target) == target


@pytest.mark.parametrize(
    "target",
    [
        "",
        "classes",
        "//evil.example",
        "///evil.example",
        "/\\evil.example",
        "\\\\evil.example",
        "/\\/evil.example",
        "https://evil.example/",
        "http://evil.example",
        "javascript:alert(1)",
        "evil.example",
        "/\t/evil.example",
        "/\n/evil.example",
        "/\r\nSet-Cookie: x=1",
    ],
)
def test_anything_that_is_not_a_local_path_falls_back_to_the_front_page(
    target: str,
) -> None:
    assert local_path(target) == "/"
