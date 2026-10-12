"""Adapters satisfying core.generation's ProviderQuota Protocol.

OpenRouterProviderQuota reads the account's free-model daily counter
(`data.free_model_daily_requests`, reset at UTC midnight = 07:00 in Bangkok).
OpenRouter reports nothing for a BYOK or paid model, and its per-minute limit
is not reported at all, so neither is invented here.
"""

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from questly.core.generation.models import ProviderQuotaSnapshot, QuotaKind
from questly.core.generation.ports import Clock

logger = logging.getLogger(__name__)

_CACHE_SECONDS = 30
_FREE_MODEL_SUFFIX = ":free"


class _FreeModelCounter(Protocol):
    used: int
    limit: int
    remaining: int


class _KeyData(Protocol):
    free_model_daily_requests: _FreeModelCounter


class _KeyMetadata(Protocol):
    data: _KeyData


class _ApiKeys(Protocol):
    def get_current_key_metadata(self) -> _KeyMetadata: ...


class KeyMetadataClient(Protocol):
    """The slice of `openrouter.OpenRouter` this adapter uses."""

    @property
    def api_keys(self) -> _ApiKeys: ...


def utc_day_start(now: datetime) -> datetime:
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def next_utc_midnight(now: datetime) -> datetime:
    return utc_day_start(now) + timedelta(days=1)


class OpenRouterProviderQuota:
    def __init__(
        self,
        client: KeyMetadataClient,
        model: Callable[[], str],
        generations_since: Callable[[datetime], int],
        clock: Clock,
    ) -> None:
        # `model` is read on every snapshot, like the generation client reads
        # it, so an Admin's A-01 model change shows from the next page load.
        self._client = client
        self._model = model
        self._generations_since = generations_since
        self._clock = clock
        self._lock = threading.Lock()
        self._cached: tuple[datetime, ProviderQuotaSnapshot] | None = None

    def snapshot(self) -> ProviderQuotaSnapshot:
        model = self._model()
        if not model.endswith(_FREE_MODEL_SUFFIX):
            return self._unmetered(model)
        now = self._clock.now()
        with self._lock:
            if self._cached is not None:
                cached_at, snapshot = self._cached
                if now - cached_at < timedelta(seconds=_CACHE_SECONDS):
                    return snapshot
            snapshot = self._read(now)
            self._cached = (now, snapshot)
            return snapshot

    def invalidate(self) -> None:
        with self._lock:
            self._cached = None

    def _read(self, now: datetime) -> ProviderQuotaSnapshot:
        try:
            counter = self._client.api_keys.get_current_key_metadata().data
            free = counter.free_model_daily_requests
            return ProviderQuotaSnapshot(
                kind=QuotaKind.EXACT,
                used=free.used,
                limit=free.limit,
                remaining=free.remaining,
                resets_at=next_utc_midnight(now),
                note="",
            )
        except Exception:  # noqa: BLE001 -- the quota line must never break T-03
            logger.exception("could not read the OpenRouter free-model quota")
            return ProviderQuotaSnapshot(
                kind=QuotaKind.UNKNOWN,
                resets_at=next_utc_midnight(now),
                note="Could not read the OpenRouter free quota right now.",
            )

    def _unmetered(self, model: str) -> ProviderQuotaSnapshot:
        now = self._clock.now()
        done = self._generations_since(utc_day_start(now))
        return ProviderQuotaSnapshot(
            kind=QuotaKind.UNKNOWN,
            resets_at=next_utc_midnight(now),
            note=(
                f"{model} is not a free model, so OpenRouter reports no quota. "
                f"{done} generations succeeded today."
            ),
        )


class StubProviderQuota:
    """Demo mode and CI: no API key, so nothing is measured."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def snapshot(self) -> ProviderQuotaSnapshot:
        return ProviderQuotaSnapshot(
            kind=QuotaKind.DEMO,
            resets_at=next_utc_midnight(self._clock.now()),
            note="Demo mode: the OpenRouter quota is not measured.",
        )

    def invalidate(self) -> None:
        pass
