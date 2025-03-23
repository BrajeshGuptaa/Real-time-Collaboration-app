import uuid
from dataclasses import dataclass

from rt_collab.services.crdt import TextCRDT


@dataclass
class DocState:
    crdt: TextCRDT
    version: int = 0


class InMemoryDocStore:
    def __init__(self) -> None:
        self._docs: dict[uuid.UUID, DocState] = {}

    async def get_or_create(self, doc_id: uuid.UUID) -> DocState:
        if doc_id not in self._docs:
            self._docs[doc_id] = DocState(TextCRDT(site_id=str(doc_id)))
        return self._docs[doc_id]

    async def apply_ops(self, doc_id: uuid.UUID, op: dict) -> int:
        doc = await self.get_or_create(doc_id)
        doc.crdt.apply(op)
        doc.version += 1
        return doc.version
