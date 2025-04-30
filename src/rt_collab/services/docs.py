from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from rt_collab.services.crdt import TextCRDT


@dataclass
class DocState:
    crdt: TextCRDT
    version: int = 0  # monotonically increasing with each op batch applied
    ops_applied: int = 0
    last_activity: datetime | None = None


class InMemoryDocStore:
    """Simple in-memory store for active documents.
    In production, hydrate from DB snapshots and tail ops on demand.
    """

    def __init__(self) -> None:
        self._docs: Dict[uuid.UUID, DocState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, doc_id: uuid.UUID) -> DocState:
        async with self._lock:
            if doc_id not in self._docs:
                self._docs[doc_id] = DocState(TextCRDT(site_id=str(doc_id)))
            return self._docs[doc_id]

    async def apply_ops(self, doc_id: uuid.UUID, op_batch: dict) -> int:
        doc = await self.get_or_create(doc_id)
        doc.crdt.apply(op_batch)
        doc.version += 1
        doc.ops_applied += 1
        doc.last_activity = datetime.utcnow()
        return doc.version

    async def snapshot_text(self, doc_id: uuid.UUID) -> tuple[str, int]:
        doc = await self.get_or_create(doc_id)
        return doc.crdt.to_string(), doc.version

    async def local_insert(self, doc_id: uuid.UUID, index: int, text: str) -> tuple[dict, int, str]:
        doc = await self.get_or_create(doc_id)
        op = doc.crdt.local_insert(index, text)
        doc.version += 1
        doc.ops_applied += 1
        doc.last_activity = datetime.utcnow()
        new_text = doc.crdt.to_string()
        return op, doc.version, new_text

    async def local_delete(self, doc_id: uuid.UUID, index: int, length: int) -> tuple[dict, int, str]:
        doc = await self.get_or_create(doc_id)
        op = doc.crdt.local_delete(index, length)
        doc.version += 1
        doc.ops_applied += 1
        doc.last_activity = datetime.utcnow()
        new_text = doc.crdt.to_string()
        return op, doc.version, new_text

    async def stats(self, doc_id: uuid.UUID) -> dict:
        doc = await self.get_or_create(doc_id)
        return {
            "version": doc.version,
            "ops_applied": doc.ops_applied,
            "length": len(doc.crdt.to_string()),
            "last_activity": doc.last_activity,
        }

    async def reset(self) -> None:
        async with self._lock:
            self._docs = {}


store = InMemoryDocStore()
