import uuid

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1")


class CreateDocRequest(BaseModel):
    title: str = "Untitled"


class CreateDocResponse(BaseModel):
    id: uuid.UUID
    title: str


@router.post("/docs", response_model=CreateDocResponse)
async def create_doc(req: CreateDocRequest) -> CreateDocResponse:
    return CreateDocResponse(id=uuid.uuid4(), title=req.title)


class GetDocResponse(BaseModel):
    id: uuid.UUID
    text: str
    version: int


@router.get("/docs/{doc_id}", response_model=GetDocResponse)
async def get_doc(doc_id: uuid.UUID) -> GetDocResponse:
    return GetDocResponse(id=doc_id, text="", version=0)
