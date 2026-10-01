"""Stand-in for a SQL adapter whose tables are not migrated yet.

ADR-0007 §10.4: until OPS-15 lands the classroom tables, `create_app()` wires
this in place of the missing SQL repository. Any call raises
SliceNotPersistedError, which main.py answers with 503, so the routers stay
mounted (and visible in /docs) while nothing pretends to persist. It is not an
in-memory store: it holds no data at all.
"""

from collections.abc import Callable
from typing import NoReturn


class SliceNotPersistedError(RuntimeError):
    """The slice has no tables yet; answered with 503 by main.py."""


class PendingRepository:
    """Satisfies any repository Protocol by refusing every call."""

    __slots__ = ("_slice_name",)

    def __init__(self, slice_name: str) -> None:
        self._slice_name = slice_name

    def __getattr__(self, name: str) -> Callable[..., NoReturn]:
        raise SliceNotPersistedError(
            f"{self._slice_name} is not persisted yet (ADR-0007, OPS-15)"
        )
