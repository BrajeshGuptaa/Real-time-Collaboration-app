from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict

from rt_collab.services.docs import store
from rt_collab.services.notifications import notification_log
from rt_collab.services.snapshots import snapshots
from rt_collab.services.task_queue import RetryableError, TaskQueue


async def handle_snapshot_create(payload: Dict[str, object]) -> Dict[str, object]:
    doc_id = uuid.UUID(str(payload.get("doc_id")))
    text, version = await store.snapshot_text(doc_id)
    snap = await snapshots.record(doc_id, version, text)
    return {"doc_id": str(doc_id), "version": version, "created_at": snap.created_at.isoformat()}


async def handle_doc_export(payload: Dict[str, object]) -> Dict[str, object]:
    doc_id = uuid.UUID(str(payload.get("doc_id")))
    export_format = str(payload.get("format") or "markdown")
    text, version = await store.snapshot_text(doc_id)
    meta = {
        "doc_id": str(doc_id),
        "version": version,
        "exported_at": datetime.utcnow().isoformat(),
        "format": export_format,
    }
    if export_format == "markdown":
        meta["content"] = f"# Doc {doc_id}\\n\\n{str(text)}"
    else:
        meta["content"] = str(text)
    return meta


async def handle_activity_digest(payload: Dict[str, object]) -> Dict[str, object]:
    doc_id = uuid.UUID(str(payload.get("doc_id")))
    stats = await store.stats(doc_id)
    latest_snapshot = await snapshots.latest(doc_id)
    return {
        "doc_id": str(doc_id),
        "ops_applied": stats["ops_applied"],
        "version": stats["version"],
        "length": stats["length"],
        "last_activity": stats["last_activity"].isoformat() if stats["last_activity"] else None,
        "last_snapshot_version": latest_snapshot.version if latest_snapshot else None,
    }


async def handle_email_notify(payload: Dict[str, object]) -> Dict[str, object]:
    recipients = payload.get("recipients") or []
    if not isinstance(recipients, list) or not recipients:
        raise RetryableError("no_recipients")
    doc_id = str(payload.get("doc_id"))
    message = str(payload.get("message") or "")
    for r in recipients:
        await notification_log.record(str(r), doc_id, message)
    return {"count": len(recipients), "doc_id": doc_id}


async def handle_backup_run(payload: Dict[str, object]) -> Dict[str, object]:
    # Pretend to back up all known docs by copying their latest state
    doc_ids = await store.list_doc_ids()
    backed_up = []
    for doc_id in doc_ids:
        text, version = await store.snapshot_text(doc_id)
        await snapshots.record(doc_id, version, text)
        backed_up.append({"doc_id": str(doc_id), "version": version})
    return {"backed_up": backed_up, "count": len(backed_up)}


def register_default_handlers(queue: TaskQueue) -> None:
    queue.register_handler("snapshot.create", handle_snapshot_create)
    queue.register_handler("doc.export", handle_doc_export)
    queue.register_handler("activity.digest", handle_activity_digest)
    queue.register_handler("email.notify", handle_email_notify)
    queue.register_handler("backup.run", handle_backup_run)
