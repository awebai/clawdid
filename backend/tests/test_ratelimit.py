from __future__ import annotations

import time

import pytest

from clawdid.ratelimit import MemoryFixedWindowRateLimiter


@pytest.mark.asyncio
async def test_memory_fixed_window_allows_then_blocks(monkeypatch):
    t = 1_700_000_000.0

    def _now() -> float:
        return t

    monkeypatch.setattr(time, "time", _now)

    limiter = MemoryFixedWindowRateLimiter()

    d1 = await limiter.hit(
        bucket="did_key", key="127.0.0.1", limit=2, window_seconds=60
    )
    assert d1.allowed is True
    assert d1.remaining == 1

    d2 = await limiter.hit(
        bucket="did_key", key="127.0.0.1", limit=2, window_seconds=60
    )
    assert d2.allowed is True
    assert d2.remaining == 0

    d3 = await limiter.hit(
        bucket="did_key", key="127.0.0.1", limit=2, window_seconds=60
    )
    assert d3.allowed is False
    assert d3.remaining == 0


@pytest.mark.asyncio
async def test_memory_fixed_window_resets_next_window(monkeypatch):
    t = 1_700_000_000.0

    def _now() -> float:
        return t

    monkeypatch.setattr(time, "time", _now)

    limiter = MemoryFixedWindowRateLimiter()
    d1 = await limiter.hit(
        bucket="did_log", key="127.0.0.1", limit=1, window_seconds=60
    )
    assert d1.allowed is True

    d2 = await limiter.hit(
        bucket="did_log", key="127.0.0.1", limit=1, window_seconds=60
    )
    assert d2.allowed is False

    t += 61
    d3 = await limiter.hit(
        bucket="did_log", key="127.0.0.1", limit=1, window_seconds=60
    )
    assert d3.allowed is True
