"""Fixtures several contracts share.

A contract that needs a row in another table (an owner, a Classroom) asks for a
factory fixture instead of building the row itself. The in-memory bindings get
the defaults here, which only hand out fresh ids; the SQL bindings in
`tests/db/` override them with factories that insert real rows, so foreign keys
hold.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import count

import pytest

IdFactory = Callable[[], int]


@dataclass(frozen=True, slots=True)
class PostingIds:
    """Where a Posting sits: its own id and the two it joins."""

    posting_id: int
    classroom_id: int
    assignment_id: int


PostingFactory = Callable[[], PostingIds]


class NeedsUsers:
    """Mixin for contracts whose rows point at accounts."""

    @pytest.fixture()
    def new_user(self) -> IdFactory:
        ids = count(1)
        return lambda: next(ids)


class NeedsClassrooms(NeedsUsers):
    """Mixin for contracts whose rows point at Classrooms."""

    @pytest.fixture()
    def new_classroom(self) -> IdFactory:
        ids = count(1)
        return lambda: next(ids)


class NeedsAssignments(NeedsClassrooms):
    """Mixin for contracts whose rows point at Assignments."""

    @pytest.fixture()
    def new_assignment(self) -> IdFactory:
        ids = count(1)
        return lambda: next(ids)


class NeedsTopics:
    """Mixin for contracts whose rows point at Topics."""

    @pytest.fixture()
    def new_topic(self) -> IdFactory:
        ids = count(1)
        return lambda: next(ids)


class NeedsPostings(NeedsAssignments):
    """Mixin for contracts whose rows point at Postings."""

    @pytest.fixture()
    def new_posting(self) -> PostingFactory:
        ids = count(1)

        def create() -> PostingIds:
            posting_id = next(ids)
            return PostingIds(posting_id, 100 + posting_id, 200 + posting_id)

        return create
