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
