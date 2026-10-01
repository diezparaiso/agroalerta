import asyncio

import pytest

from app.core.async_cache import AsyncTTLCache


def test_cache_reuses_successful_result():
    async def scenario():
        cache = AsyncTTLCache(ttl_seconds=60)
        calls = 0

        async def factory():
            nonlocal calls
            calls += 1
            return {"items": [1, 2]}

        first = await cache.get_or_create("same-query", factory)
        first["items"].append(3)
        second = await cache.get_or_create("same-query", factory)
        assert calls == 1
        assert second == {"items": [1, 2]}

    asyncio.run(scenario())


def test_concurrent_identical_requests_are_deduplicated():
    async def scenario():
        cache = AsyncTTLCache(ttl_seconds=60)
        calls = 0
        gate = asyncio.Event()

        async def factory():
            nonlocal calls
            calls += 1
            await gate.wait()
            return {"value": 42}

        first = asyncio.create_task(cache.get_or_create("query", factory))
        second = asyncio.create_task(cache.get_or_create("query", factory))
        await asyncio.sleep(0)
        gate.set()
        results = await asyncio.gather(first, second)
        assert calls == 1
        assert results == [{"value": 42}, {"value": 42}]

    asyncio.run(scenario())


def test_failed_factory_is_not_cached_and_can_be_retried():
    async def scenario():
        cache = AsyncTTLCache(ttl_seconds=60)
        calls = 0

        async def factory():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("temporary provider error")
            return {"ok": True}

        with pytest.raises(RuntimeError, match="temporary provider error"):
            await cache.get_or_create("query", factory)
        assert await cache.get_or_create("query", factory) == {"ok": True}
        assert calls == 2

    asyncio.run(scenario())


def test_cache_rejects_invalid_limits():
    with pytest.raises(ValueError):
        AsyncTTLCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        AsyncTTLCache(ttl_seconds=1, max_entries=0)
