from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from rt_collab.api.jobs import JobResponse
from rt_collab.services.docs import store
from rt_collab.services.task_queue import Job, task_queue


router = APIRouter(prefix="/v1")


class CreateDocRequest(BaseModel):
    title: str = "Untitled"
    created_by: str | None = None


class CreateDocResponse(BaseModel):
    id: uuid.UUID
    title: str


@router.post("/docs", response_model=CreateDocResponse)
async def create_doc(req: CreateDocRequest) -> Any:
    # In-memory only for MVP; DB persistence can be added later
    doc_id = uuid.uuid4()
    await store.get_or_create(doc_id)
    return CreateDocResponse(id=doc_id, title=req.title)


class GetDocResponse(BaseModel):
    id: uuid.UUID
    text: str
    version: int


@router.get("/docs/{doc_id}", response_model=GetDocResponse)
async def get_doc(doc_id: uuid.UUID) -> Any:
    try:
        text, version = await store.snapshot_text(doc_id)
    except Exception as e:  # noqa: F841
        # If not created yet, return empty
        await store.get_or_create(doc_id)
        text, version = "", 0
    return GetDocResponse(id=doc_id, text=text, version=version)


class ExportDocRequest(BaseModel):
    format: str = "markdown"


def _job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        type=job.type,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        idempotency_key=job.idempotency_key,
        request_id=job.request_id,
        enqueued_at=job.enqueued_at,
        next_run_at=job.next_run_at,
        result=job.result,
        error=job.error,
    )


@router.post("/docs/{doc_id}/export", response_model=JobResponse)
async def export_doc(doc_id: uuid.UUID, req: ExportDocRequest, request: Request) -> Any:
    job = await task_queue.enqueue(
        "doc.export",
        {"doc_id": str(doc_id), "format": req.format},
        idempotency_key=f"export-{doc_id}-{req.format}",
        request_id=getattr(request.state, "request_id", None),
    )
    return _job_to_response(job)


@router.post("/docs/{doc_id}/digest", response_model=JobResponse)
async def digest_doc(doc_id: uuid.UUID, request: Request) -> Any:
    job = await task_queue.enqueue(
        "activity.digest",
        {"doc_id": str(doc_id)},
        idempotency_key=f"digest-{doc_id}",
        request_id=getattr(request.state, "request_id", None),
    )
    return _job_to_response(job)
