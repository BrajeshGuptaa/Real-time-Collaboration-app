from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rt_collab.services.docs import store


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

