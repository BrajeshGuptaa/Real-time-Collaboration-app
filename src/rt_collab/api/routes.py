import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from rt_collab.services.docs import InMemoryDocStore

router = APIRouter(prefix="/v1")
store = InMemoryDocStore()


class CreateDocRequest(BaseModel):
    title: str = "Untitled"


class CreateDocResponse(BaseModel):
    id: uuid.UUID
    title: str


@router.post("/docs", response_model=CreateDocResponse)
async def create_doc(req: CreateDocRequest) -> CreateDocResponse:
    doc_id = uuid.uuid4()
    await store.get_or_create(doc_id)
    return CreateDocResponse(id=doc_id, title=req.title)


class GetDocResponse(BaseModel):
    id: uuid.UUID
    text: str
    version: int


@router.get("/docs/{doc_id}", response_model=GetDocResponse)
async def get_doc(doc_id: uuid.UUID) -> GetDocResponse:
    doc = await store.get_or_create(doc_id)
    return GetDocResponse(id=doc_id, text=doc.crdt.to_string(), version=doc.version)
