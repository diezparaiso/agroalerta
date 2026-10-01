"""Bounded process-local async TTL cache with in-flight request deduplication.

This cache is an optimization for one application process, not a distributed
cache. Keys must include all result-affecting parameters and authorization scope.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from copy import deepcopy
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncTTLCache:
    def __init__(self, ttl_seconds: float, max_entries: int = 256) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds debe ser mayor que cero")
        if max_entries < 1:
            raise ValueError("max_entries debe ser al menos 1")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._values: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._in_flight: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            now = time.monotonic()
            cached = self._values.get(key)
            if cached is not None:
                expires_at, value = cached
                if expires_at > now:
                    self._values.move_to_end(key)
                    return deepcopy(value)
                del self._values[key]

            task = self._in_flight.get(key)
            if task is None:
                task = asyncio.create_task(factory())
                self._in_flight[key] = task
                task.add_done_callback(
                    lambda completed, cache_key=key: asyncio.create_task(
                        self._finish(cache_key, completed)
                    )
                )

        # One caller being cancelled must not cancel work shared by other callers.
        return deepcopy(await asyncio.shield(task))

    async def _finish(self, key: str, task: asyncio.Task[Any]) -> None:
        async with self._lock:
            if self._in_flight.get(key) is not task:
                return
            del self._in_flight[key]
            if task.cancelled() or task.exception() is not None:
                return
            self._values[key] = (time.monotonic() + self.ttl_seconds, task.result())
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)

    async def clear(self) -> None:
        async with self._lock:
            self._values.clear()
