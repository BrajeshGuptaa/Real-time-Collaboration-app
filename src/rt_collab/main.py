from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from rt_collab.api.routes import router as api_router
from rt_collab.api.jobs import router as jobs_router
from rt_collab.core.config import get_settings
from rt_collab.services.docs import store
from rt_collab.services.job_handlers import register_default_handlers
from rt_collab.services.task_queue import task_queue
from rt_collab.ws.manager import manager


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    # Simple tracing hook to correlate requests and downstream async jobs
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.get("/healthz")
async def healthz() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> Dict[str, Any]:
    return {"status": "ready"}


@app.on_event("startup")
async def startup_events() -> None:
    register_default_handlers(task_queue)
    await task_queue.start()


@app.on_event("shutdown")
async def shutdown_events() -> None:
    await task_queue.stop()


@app.get("/metrics")
async def metrics() -> Response:
    summary = task_queue.metrics.summary()
    lines = [
        "# HELP queue_jobs_total Total jobs processed by status",
        "# TYPE queue_jobs_total counter",
    ]
    for status, count in summary.items():
        if status in {"retries", "p95_latency_ms"}:
            continue
        lines.append(f'queue_jobs_total{{status="{status}"}} {count}')
    lines.append("# HELP queue_job_latency_p95_ms 95th percentile latency in ms")
    lines.append("# TYPE queue_job_latency_p95_ms gauge")
    lines.append(f'queue_job_latency_p95_ms {summary.get("p95_latency_ms", 0.0)}')
    lines.append("# HELP queue_retries_total Retry attempts recorded")
    lines.append("# TYPE queue_retries_total counter")
    lines.append(f'queue_retries_total {summary.get("retries", 0)}')
    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain")


app.include_router(api_router)
app.include_router(jobs_router)


@app.websocket("/v1/ws/docs/{doc_id}")
async def ws_docs(doc_id: uuid.UUID, websocket: WebSocket) -> None:
    await manager.connect(doc_id, websocket)
    # On join, send current snapshot
    text, version = await store.snapshot_text(doc_id)
    await websocket.send_text(json.dumps({"type": "snapshot", "text": text, "version": version}))
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "nack", "reason": "invalid_json"}))
                continue

            t = data.get("type")
            if t == "op.submit":
                op = data.get("op")
                if not isinstance(op, dict):
                    await websocket.send_text(json.dumps({"type": "nack", "reason": "invalid_op"}))
                    continue
                new_version = await store.apply_ops(doc_id, op)
                # Also broadcast updated text for simple clients
                text_now, _ = await store.snapshot_text(doc_id)
                # Ack the sender and broadcast update to others
                await websocket.send_text(json.dumps({"type": "ack", "version": new_version, "text": text_now}))
                await manager.broadcast(doc_id, {"type": "doc.update", "version": new_version, "text": text_now}, exclude=websocket)
            elif t == "edit.insert":
                try:
                    index = int(data.get("index"))
                    text_ins = str(data.get("text", ""))
                except Exception:
                    await websocket.send_text(json.dumps({"type": "nack", "reason": "bad_insert_args"}))
                    continue
                _, version2, text_now = await store.local_insert(doc_id, index, text_ins)
                await websocket.send_text(json.dumps({"type": "ack", "version": version2, "text": text_now}))
                await manager.broadcast(doc_id, {"type": "doc.update", "version": version2, "text": text_now}, exclude=websocket)
            elif t == "edit.delete":
                try:
                    index = int(data.get("index"))
                    length = int(data.get("length"))
                except Exception:
                    await websocket.send_text(json.dumps({"type": "nack", "reason": "bad_delete_args"}))
                    continue
                _, version3, text_now = await store.local_delete(doc_id, index, length)
                await websocket.send_text(json.dumps({"type": "ack", "version": version3, "text": text_now}))
                await manager.broadcast(doc_id, {"type": "doc.update", "version": version3, "text": text_now}, exclude=websocket)
            elif t == "cursor.update":
                # Broadcast presence/cursor updates to others (no persistence)
                payload = {"type": "presence.cursor", "data": data.get("data", {}), "ts": data.get("ts")}
                await manager.broadcast(doc_id, payload, exclude=websocket)
            else:
                await websocket.send_text(json.dumps({"type": "nack", "reason": "unknown_type"}))
    except WebSocketDisconnect:
        await manager.disconnect(doc_id, websocket)


# Serve a tiny demo UI (resolve path relative to this file)
_here = Path(__file__).resolve()
_web_dir = _here.parents[2] / "web"
if _web_dir.exists():
    # Serve UI at /ui to avoid masking API routes
    app.mount("/ui", StaticFiles(directory=str(_web_dir), html=True), name="ui")

    @app.get("/")
    async def root_redirect():
        return RedirectResponse(url="/ui/")
