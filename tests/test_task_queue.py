from __future__ import annotations

import asyncio

import pytest

from rt_collab.services.task_queue import RetryableError, TaskQueue


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def wait_for_status(queue: TaskQueue, job_id, targets: set[str], timeout: float = 3.0):
    start = asyncio.get_event_loop().time()
    while True:
        job = queue.get_job(job_id)
        if job and job.status in targets:
            return job
        if asyncio.get_event_loop().time() - start > timeout:
            raise AssertionError(f"timeout waiting for {targets}")
        await asyncio.sleep(0.05)


@pytest.mark.anyio
async def test_retry_and_dlq():
    queue = TaskQueue()
    attempts = {"count": 0}

    async def flaky(payload):
        attempts["count"] += 1
        raise RetryableError("boom")

    queue.register_handler("flaky", flaky)
    await queue.start()
    job = await queue.enqueue("flaky", {}, max_attempts=2)

    finished = await wait_for_status(queue, job.id, {"dead"})
    await queue.stop()

    assert attempts["count"] == 2
    assert finished.status == "dead"


@pytest.mark.anyio
async def test_idempotent_enqueue_reuses_job():
    queue = TaskQueue()

    async def ok(payload):
        return {"ok": True}

    queue.register_handler("ok", ok)
    await queue.start()

    job1 = await queue.enqueue("ok", {}, idempotency_key="same")
    job2 = await queue.enqueue("ok", {}, idempotency_key="same")

    result = await wait_for_status(queue, job1.id, {"succeeded"})
    await queue.stop()

    assert job1.id == job2.id
    assert result.result == {"ok": True}
