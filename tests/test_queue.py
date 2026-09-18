import asyncio
from krbi_agent.queue import TaskQueue

def test_queue_priority_and_parallel_workers():
    async def run():
        seen = []
        async def worker(value):
            seen.append(value)
            await asyncio.sleep(0.01)
            return value * 2
        q = TaskQueue(worker, max_workers=2, max_pending=8)
        await q.start()
        try:
            results = await asyncio.gather(q.submit(1, priority=20), q.submit(2, priority=1), q.submit(3, priority=10))
            assert sorted(results) == [2, 4, 6]
            assert q.qsize() == 0
            assert len(seen) == 3
            stats = q.stats()
            assert stats["submitted"] == 3
            assert stats["completed"] == 3
        finally:
            await q.close()

    asyncio.run(run())

def test_queue_rejects_submit_after_close():
    async def run():
        async def worker(value):
            return value
        q = TaskQueue(worker)
        await q.start()
        await q.close()
        try:
            await q.submit("x")
        except RuntimeError:
            return
        raise AssertionError("closed queue accepted work")
    asyncio.run(run())
