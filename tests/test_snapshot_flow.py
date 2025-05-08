from __future__ import annotations

import asyncio
import os
import uuid

import pytest

from rt_collab.core.config import get_settings
from rt_collab.services.docs import store
from rt_collab.services.job_handlers import register_default_handlers
from rt_collab.services.snapshots import snapshots
from rt_collab.services.task_queue import task_queue


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def wait_for_job_of_type(job_type: str, targets: set[str], timeout: float = 5.0):
    start = asyncio.get_event_loop().time()
    last_seen = None
    while True:
        for job in task_queue.all_jobs().values():
            if job.type == job_type and job.status in targets:
                return job
            if job.type == job_type:
                last_seen = job.status
        if asyncio.get_event_loop().time() - start > timeout:
            raise AssertionError(f"timeout waiting for job (last_seen={last_seen})")
        await asyncio.sleep(0.05)


@pytest.mark.anyio
async def test_snapshot_job_runs_when_interval_hits(monkeypatch):
    os.environ["SNAPSHOT_INTERVAL"] = "1"
    get_settings.cache_clear()

    await task_queue.reset()
    register_default_handlers(task_queue)
    await store.reset()
    await snapshots.reset()
    await task_queue.start()

    doc_id = uuid.uuid4()
    await store.local_insert(doc_id, 0, "hello async world")

    job = await wait_for_job_of_type("snapshot.create", {"succeeded"})
    latest = await snapshots.latest(doc_id)

    await task_queue.stop()
    os.environ["SNAPSHOT_INTERVAL"] = "100"
    get_settings.cache_clear()

    assert job.status == "succeeded"
    assert latest is not None
    assert latest.text == "hello async world"
