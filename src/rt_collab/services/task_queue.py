from __future__ import annotations

import asyncio
import heapq
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

from rt_collab.core.metrics import QueueMetrics


class RetryableError(Exception):
    """Marker error to request a retry with backoff."""


class JobStatus(str):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    dead = "dead"


Handler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any] | None]]


@dataclass
class Job:
    id: uuid.UUID
    type: str
    payload: Dict[str, Any]
    status: str = JobStatus.queued
    attempts: int = 0
    max_attempts: int = 3
    idempotency_key: str | None = None
    enqueued_at: datetime = field(default_factory=datetime.utcnow)
    next_run_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    result: Dict[str, Any] | None = None
    error: str | None = None

    def mark_running(self) -> None:
        self.status = JobStatus.running
        self.updated_at = datetime.utcnow()

    def mark_complete(self, result: Dict[str, Any] | None = None) -> None:
        self.status = JobStatus.succeeded
        self.result = result
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        self.status = JobStatus.failed
        self.error = error
        self.updated_at = datetime.utcnow()

    def mark_dead(self, error: str) -> None:
        self.status = JobStatus.dead
        self.error = error
        self.updated_at = datetime.utcnow()


class TaskQueue:
    def __init__(self) -> None:
        self._handlers: Dict[str, Handler] = {}
        self._jobs: Dict[uuid.UUID, Job] = {}
        self._idempotency: Dict[str, uuid.UUID] = {}
        self._pending: list[tuple[float, uuid.UUID]] = []
        self._wake = asyncio.Event()
        self._worker: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stopped = False
        self.metrics = QueueMetrics()

    def register_handler(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    async def enqueue(self, job_type: str, payload: Dict[str, Any], *, idempotency_key: str | None = None, max_attempts: int = 3) -> Job:
        async with self._lock:
            if idempotency_key and idempotency_key in self._idempotency:
                return self._jobs[self._idempotency[idempotency_key]]

            job_id = uuid.uuid4()
            job = Job(
                id=job_id,
                type=job_type,
                payload=payload,
                max_attempts=max_attempts,
                idempotency_key=idempotency_key,
            )
            self._jobs[job_id] = job
            if idempotency_key:
                self._idempotency[idempotency_key] = job_id
            heapq.heappush(self._pending, (job.next_run_at.timestamp(), job.id))
            self.metrics.record_status(JobStatus.queued)
            self._wake.set()
            return job

    async def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._stopped = False
        self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stopped = True
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while not self._stopped:
            job_id = await self._next_ready_job()
            if job_id is None:
                # Sleep briefly to avoid busy loop if no jobs exist
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=0.25)
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
                continue
            await self._execute(job_id)

    async def _next_ready_job(self) -> uuid.UUID | None:
        async with self._lock:
            if not self._pending:
                return None
            ts, job_id = self._pending[0]
            now_ts = datetime.utcnow().timestamp()
            if ts > now_ts:
                return None
            heapq.heappop(self._pending)
            return job_id

    async def _execute(self, job_id: uuid.UUID) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        handler = self._handlers.get(job.type)
        if not handler:
            job.mark_dead("no_handler")
            return
        job.mark_running()
        self.metrics.record_status(JobStatus.running)
        start_ms = time.perf_counter() * 1000
        try:
            result = await handler(job.payload)
            job.mark_complete(result)
            self.metrics.record_status(JobStatus.succeeded)
            self.metrics.record_latency(time.perf_counter() * 1000 - start_ms)
        except RetryableError as exc:
            job.attempts += 1
            if job.attempts >= job.max_attempts:
                job.mark_dead(str(exc))
                self.metrics.record_status(JobStatus.dead)
                return
            delay = self._backoff(job.attempts)
            job.status = JobStatus.queued
            job.next_run_at = datetime.utcnow() + timedelta(seconds=delay)
            job.updated_at = datetime.utcnow()
            self.metrics.record_retry()
            async with self._lock:
                heapq.heappush(self._pending, (job.next_run_at.timestamp(), job.id))
                self._wake.set()
        except Exception as exc:  # pragma: no cover - debug aid
            job.mark_dead(str(exc))
            self.metrics.record_status(JobStatus.dead)

    def _backoff(self, attempt: int) -> float:
        base = 2 ** (attempt - 1)
        return base + random.random()

    def get_job(self, job_id: uuid.UUID) -> Optional[Job]:
        return self._jobs.get(job_id)

    def all_jobs(self) -> Dict[uuid.UUID, Job]:
        return dict(self._jobs)


task_queue = TaskQueue()
