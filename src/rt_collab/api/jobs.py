from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from rt_collab.services.task_queue import Job, task_queue


router = APIRouter(prefix="/v1")

ALLOWED_JOB_TYPES = {
    "snapshot.create",
    "doc.export",
    "activity.digest",
    "email.notify",
    "backup.run",
}


class JobCreateRequest(BaseModel):
    type: str = Field(..., description="Job type identifier")
    payload: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    max_attempts: int = 3


class JobResponse(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    attempts: int
    max_attempts: int
    idempotency_key: str | None
    request_id: str | None
    enqueued_at: datetime
    next_run_at: datetime
    result: Dict[str, Any] | None
    error: str | None


def _serialize_job(job: Job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "attempts": job.attempts,
        "max_attempts": job.max_attempts,
        "idempotency_key": job.idempotency_key,
        "request_id": job.request_id,
        "enqueued_at": job.enqueued_at,
        "next_run_at": job.next_run_at,
        "result": job.result,
        "error": job.error,
    }


@router.post("/jobs", response_model=JobResponse)
async def create_job(req: JobCreateRequest, request: Request) -> Any:
    if req.type not in ALLOWED_JOB_TYPES:
        raise HTTPException(status_code=400, detail="unsupported_type")
    job = await task_queue.enqueue(
        req.type,
        req.payload,
        idempotency_key=req.idempotency_key,
        max_attempts=req.max_attempts,
        request_id=getattr(request.state, "request_id", None),
    )
    return _serialize_job(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID) -> Any:
    job = task_queue.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="not_found")
    return _serialize_job(job)
