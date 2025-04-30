from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Snapshot:
    doc_id: uuid.UUID
    version: int
    text: str
    created_at: datetime


class InMemorySnapshotStore:
    def __init__(self) -> None:
        self._snapshots: Dict[uuid.UUID, List[Snapshot]] = {}
        self._lock = asyncio.Lock()

    async def record(self, doc_id: uuid.UUID, version: int, text: str) -> Snapshot:
        snap = Snapshot(doc_id=doc_id, version=version, text=text, created_at=datetime.utcnow())
        async with self._lock:
            self._snapshots.setdefault(doc_id, []).append(snap)
        return snap

    async def latest(self, doc_id: uuid.UUID) -> Optional[Snapshot]:
        async with self._lock:
            snaps = self._snapshots.get(doc_id, [])
            if not snaps:
                return None
            return snaps[-1]

    async def all_for_doc(self, doc_id: uuid.UUID) -> List[Snapshot]:
        async with self._lock:
            return list(self._snapshots.get(doc_id, []))

    async def reset(self) -> None:
        async with self._lock:
            self._snapshots = {}


snapshots = InMemorySnapshotStore()
