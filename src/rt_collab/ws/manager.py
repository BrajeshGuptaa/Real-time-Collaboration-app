import asyncio
import json
import uuid
from typing import Any, Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._doc_peers: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, doc_id: uuid.UUID, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._doc_peers.setdefault(doc_id, set()).add(ws)

    async def disconnect(self, doc_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            peers = self._doc_peers.get(doc_id)
            if peers and ws in peers:
                peers.remove(ws)
            if peers and len(peers) == 0:
                self._doc_peers.pop(doc_id, None)

    async def broadcast(self, doc_id: uuid.UUID, message: Dict[str, Any], exclude: WebSocket | None = None) -> None:
        peers = self._doc_peers.get(doc_id, set()).copy()
        for ws in peers:
            if ws is exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                try:
                    await ws.close()
                except Exception:
                    pass
                await self.disconnect(doc_id, ws)
