"""OpenRouterProviderQuota: the free-model daily quota, cached 30 seconds."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from questly.ai.quota import OpenRouterProviderQuota, StubProviderQuota
from questly.core.generation.models import QuotaKind
from tests.fakes.auth import FakeClock

NOW = datetime(2026, 10, 12, 10, 30, tzinfo=UTC)
NEXT_UTC_MIDNIGHT = datetime(2026, 10, 13, 0, 0, tzinfo=UTC)


@dataclass
class FakeSdk:
    """Stands in for `OpenRouter(...)`: only `api_keys.get_current_key_metadata`."""

    used: int = 13
    limit: int = 50
    remaining: int = 37
    fail: bool = False
    calls: int = 0

    @property
    def api_keys(self) -> SimpleNamespace:
        return SimpleNamespace(get_current_key_metadata=self._metadata)

    def _metadata(self) -> SimpleNamespace:
        self.calls += 1
        if self.fail:
            raise ConnectionError("no route to openrouter")
        counter = SimpleNamespace(
            used=self.used, limit=self.limit, remaining=self.remaining
        )
        return SimpleNamespace(data=SimpleNamespace(free_model_daily_requests=counter))


class World:
    def __init__(self, model: str = "openai/gpt-oss-20b:free") -> None:
        self.sdk = FakeSdk()
        self.clock = FakeClock(NOW)
        self.model = model
        self.generations_today = 4
        self.counted_since: list[datetime] = []
        self.quota = OpenRouterProviderQuota(
            self.sdk,
            model=lambda: self.model,
            generations_since=self._count_since,
            clock=self.clock,
        )

    def _count_since(self, since: datetime) -> int:
        self.counted_since.append(since)
        return self.generations_today


@pytest.fixture()
def world() -> World:
    return World()


def test_a_free_model_reports_the_exact_counter_and_the_utc_reset(world: World) -> None:
    snapshot = world.quota.snapshot()

    assert snapshot.kind is QuotaKind.EXACT
    assert (snapshot.used, snapshot.limit, snapshot.remaining) == (13, 50, 37)
    assert snapshot.resets_at == NEXT_UTC_MIDNIGHT


def test_the_answer_is_cached_for_thirty_seconds(world: World) -> None:
    world.quota.snapshot()
    world.clock.advance(timedelta(seconds=29))
    world.quota.snapshot()

    assert world.sdk.calls == 1

    world.clock.advance(timedelta(seconds=2))
    world.quota.snapshot()

    assert world.sdk.calls == 2


def test_invalidate_drops_the_cache_so_the_next_read_is_fresh(world: World) -> None:
    world.quota.snapshot()
    world.sdk.used, world.sdk.remaining = 14, 36

    world.quota.invalidate()

    assert world.quota.snapshot().remaining == 36


def test_a_model_that_is_not_free_is_unknown_and_counts_todays_successes() -> None:
    world = World(model="anthropic/claude-sonnet-5-5")

    snapshot = world.quota.snapshot()

    assert snapshot.kind is QuotaKind.UNKNOWN
    assert snapshot.remaining is None
    assert "4" in snapshot.note
    assert world.counted_since == [datetime(2026, 10, 12, 0, 0, tzinfo=UTC)]
    assert world.sdk.calls == 0


def test_the_non_free_count_is_never_stale() -> None:
    world = World(model="anthropic/claude-sonnet-5-5")
    world.quota.snapshot()
    world.generations_today = 5

    assert "5" in world.quota.snapshot().note


def test_the_admins_next_model_choice_is_honoured_without_a_restart(
    world: World,
) -> None:
    assert world.quota.snapshot().kind is QuotaKind.EXACT

    world.model = "anthropic/claude-sonnet-5-5"

    assert world.quota.snapshot().kind is QuotaKind.UNKNOWN


def test_a_provider_error_is_unknown_with_a_note_and_never_raises(world: World) -> None:
    world.sdk.fail = True

    snapshot = world.quota.snapshot()

    assert snapshot.kind is QuotaKind.UNKNOWN
    assert snapshot.note
    assert snapshot.resets_at == NEXT_UTC_MIDNIGHT


def test_a_provider_error_is_cached_too_so_the_page_stays_fast(world: World) -> None:
    world.sdk.fail = True
    world.quota.snapshot()
    world.quota.snapshot()

    assert world.sdk.calls == 1


def test_the_stub_says_it_is_a_demo() -> None:
    snapshot = StubProviderQuota(FakeClock(NOW)).snapshot()

    assert snapshot.kind is QuotaKind.DEMO
    assert snapshot.remaining is None
    assert snapshot.resets_at == NEXT_UTC_MIDNIGHT
