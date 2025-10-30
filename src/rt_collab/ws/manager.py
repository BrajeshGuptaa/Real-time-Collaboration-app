from typing import Dict, Set
from fastapi import WebSocket
import uuid


class ConnectionManager:
    def __init__(self) -> None:
        self._doc_peers: Dict[uuid.UUID, Set[WebSocket]] = {}

    async def connect(self, doc_id: uuid.UUID, ws: WebSocket) -> None:
        await ws.accept()
        self._doc_peers.setdefault(doc_id, set()).add(ws)
