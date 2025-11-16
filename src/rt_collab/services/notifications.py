from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class Notification:
    recipient: str
    doc_id: str
    message: str
    created_at: datetime


class NotificationLog:
    def __init__(self) -> None:
        self._events: List[Notification] = []
        self._lock = asyncio.Lock()

    async def record(self, recipient: str, doc_id: str, message: str) -> Notification:
        event = Notification(
            recipient=recipient,
            doc_id=doc_id,
            message=message,
            created_at=datetime.utcnow(),
        )
        async with self._lock:
            self._events.append(event)
        return event

    async def all(self) -> List[Notification]:
        async with self._lock:
            return list(self._events)

    async def reset(self) -> None:
        async with self._lock:
            self._events = []


notification_log = NotificationLog()
