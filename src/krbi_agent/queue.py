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
    """Bounded async priority queue with worker metrics and graceful shutdown."""

    def __init__(
        self,
        worker: Callable[[T], Awaitable[R]],
        max_workers: int = 4,
        max_pending: int = 32,
        name: str = "krbi",
    ):
        if max_workers < 1 or max_pending < 1:
            raise ValueError("queue limits must be positive")
        self._worker = worker
        self._queue: asyncio.PriorityQueue[
            tuple[int, int, QueueItem[T], asyncio.Future[R]]
        ] = asyncio.PriorityQueue(maxsize=max_pending)
        self._counter = count()
        self._workers: list[asyncio.Task[None]] = []
        self._started = False
        self._closed = False
        self.max_workers = max_workers
        self.max_pending = max_pending
        self.name = name
        self.submitted = 0
        self.completed = 0
        self.failed = 0
        self.cancelled = 0

    async def start(self) -> None:
        if self._started:
            return
        self._closed = False
        self._started = True
        self._workers = [
            asyncio.create_task(self._worker_loop(), name=f"{self.name}-worker-{i + 1}")
            for i in range(self.max_workers)
        ]

    async def _worker_loop(self) -> None:
        while True:
            _priority, _sequence, item, future = await self._queue.get()
            try:
                if future.cancelled():
                    self.cancelled += 1
                    continue
                try:
                    result = await self._worker(item.payload)
                    if not future.done():
                        future.set_result(result)
                    self.completed += 1
                except asyncio.CancelledError:
                    if not future.done():
                        future.cancel()
                    self.cancelled += 1
                    raise
                except BaseException as exc:
                    self.failed += 1
                    if not future.done():
                        future.set_exception(exc)
            finally:
                self._queue.task_done()

    async def submit(self, payload: T, priority: int = 100) -> R:
        if self._closed:
            raise RuntimeError(f"queue '{self.name}' is closed")
        if not self._started:
            await self.start()
        loop = asyncio.get_running_loop()
        future: asyncio.Future[R] = loop.create_future()
        item = QueueItem(next(self._counter), int(priority), payload)
        self.submitted += 1
        await self._queue.put((item.priority, item.id, item, future))
        return await future

    def qsize(self) -> int:
        return self._queue.qsize()

    def stats(self) -> dict[str, int | bool | str]:
        return {
            "name": self.name,
            "running": self._started,
            "closed": self._closed,
            "pending": self.qsize(),
            "workers": len(self._workers),
            "submitted": self.submitted,
            "completed": self.completed,
            "failed": self.failed,
            "cancelled": self.cancelled,
        }

    async def close(self, cancel_pending: bool = False) -> None:
        if not self._started:
            self._closed = True
            return
        self._closed = True
        if cancel_pending:
            while True:
                try:
                    _priority, _sequence, _item, future = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if not future.done():
                    future.cancel()
                    self.cancelled += 1
                self._queue.task_done()
        await self._queue.join()
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
