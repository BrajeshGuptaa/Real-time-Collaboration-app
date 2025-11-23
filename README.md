# Async Collaborative Docs

Real-time document editing with asynchronous background orchestration. It keeps the hot path (WebSocket ops) snappy while slow/expensive work rides the task queue.

## Stack
- FastAPI + WebSockets for HTTP and realtime
- Logoot/LSEQ-like CRDT for text inserts/deletes
- MySQL (documents/ops) and Redis (presence/pubsub) via docker compose
- SQLAlchemy (async), Pydantic settings, CORS enabled
- In-memory task queue with retries, idempotency keys, DLQ + Prometheus-style `/metrics`

## Prerequisites
- Python 3.11+
- Docker + Docker Compose (for MySQL/Redis)

## Quick start
```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start MySQL + Redis (runs in background)
docker compose up -d

# Run API with reload
PYTHONPATH=app/src uvicorn rt_collab.main:app --reload
```
- API docs: http://localhost:8000/docs  
- Demo UI: http://localhost:8000/ui/ (served from `web/`)

Stop services: `docker compose down` (data persists via the `mysqldata` volume).

## Configuration
Set via environment variables (works with a `.env` file):
- `DATABASE_URL` (async MySQL): `mysql+aiomysql://USER:PASSWORD@localhost:3306/rt_collab`
- `REDIS_URL`: `redis://localhost:6379/0` by default
- `ALLOWED_ORIGINS`: comma-separated list for CORS; default `http://localhost:3000`
- `APP_NAME`, `APP_VERSION`, `LOG_LEVEL`, `SNAPSHOT_INTERVAL`

Tip: URL-encode special characters in passwords (e.g., `@` -> `%40`).

## Endpoints
- REST: `POST /v1/docs` (create), `GET /v1/docs/{doc_id}` (snapshot), `/healthz`, `/readyz`
- WebSocket: `/v1/ws/docs/{doc_id}`  
  - Client -> server: `op.submit`, `edit.insert`, `edit.delete`, `cursor.update`  
  - Server -> client: `ack`, `doc.update`, `presence.cursor`, `snapshot`, `nack`

## Async queue API
- `POST /v1/jobs {type, payload, idempotency_key, max_attempts}` → enqueue background work
- `GET /v1/jobs/{id}` → status/result/error
- Doc helpers: `POST /v1/docs/{doc_id}/export`, `POST /v1/docs/{doc_id}/digest`
- Metrics: `/metrics` exposes counters + p95 latency for queue processing

Job types: `snapshot.create`, `doc.export`, `activity.digest`, `email.notify`, `backup.run`.

## Architecture sketch
```
clients (web/desktop)
    ↳ WebSocket: edits + presence
FastAPI collab backend
    ↳ CRDT engine (Logoot style)
    ↳ Doc store + snapshot repo
    ↳ Task Queue API (/v1/jobs)
    ↳ /metrics, /healthz, /readyz
Task Queue (in-process)
    ↳ Handlers: snapshot, export, digest, email notify, backup
    ↳ Retries with jitter, idempotency keys, DLQ
```

Example flow:
1) User edits doc → CRDT merges + increments version.  
2) Every N edits (`SNAPSHOT_INTERVAL`), a `snapshot.create` job is enqueued.  
3) Worker writes durable snapshots and updates metrics; clients keep editing uninterrupted.

## Testing
```bash
cd app
source .venv/bin/activate
pytest
```

- Property-based CRDT checks (commutativity of inserts)
- Queue lifecycle (idempotency, retry → DLQ)
- Integration: edit → snapshot job enqueued → snapshot persisted
