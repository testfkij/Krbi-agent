from __future__ import annotations

import asyncio
from dataclasses import dataclass
from itertools import count
from typing import Awaitable, Callable, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass(slots=True, frozen=True)
class QueueItem(Generic[T]):
    id: int
    priority: int
    payload: T


class TaskQueue(Generic[T, R]):
    """Small bounded async priority queue for provider/tool work."""

    def __init__(self, worker: Callable[[T], Awaitable[R]], max_workers: int = 4, max_pending: int = 32):
        if max_workers < 1 or max_pending < 1:
            raise ValueError("queue limits must be positive")
        self._worker = worker
        self._queue: asyncio.PriorityQueue[tuple[int, int, QueueItem[T], asyncio.Future[R]]] = asyncio.PriorityQueue(maxsize=max_pending)
        self._counter = count()
        self._workers: list[asyncio.Task[None]] = []
        self._started = False
        self.max_workers = max_workers
        self.max_pending = max_pending

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._workers = [asyncio.create_task(self._worker_loop()) for _ in range(self.max_workers)]

    async def _worker_loop(self) -> None:
        while True:
            priority, _, item, future = await self._queue.get()
            try:
                if future.cancelled():
                    continue
                try:
                    future.set_result(await self._worker(item.payload))
                except BaseException as exc:
                    if not future.done():
                        future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def submit(self, payload: T, priority: int = 100) -> R:
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[R] = loop.create_future()
        item = QueueItem(next(self._counter), priority, payload)
        await self._queue.put((priority, item.id, item, future))
        return await future

    def qsize(self) -> int:
        return self._queue.qsize()

    async def close(self) -> None:
        if not self._started:
            return
        await self._queue.join()
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
