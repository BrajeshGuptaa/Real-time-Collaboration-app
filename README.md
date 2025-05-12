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

## Quick start (hosted app, compose for DBs)
```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start MySQL + Redis (runs in background)
docker compose up -d mysql redis

# Run API with reload
PYTHONPATH=app/src uvicorn rt_collab.main:app --reload
```
- API docs: http://localhost:8000/docs  
- Demo UI: http://localhost:8000/ui/ (served from `web/`)

Stop services: `docker compose down` (data persists via the `mysqldata` volume).

## Run everything with Docker Compose
From `app/`:
```bash
docker compose up --build
```
- App available at http://localhost:8000 (UI at `/ui`)
- Services: FastAPI app, MySQL, Redis (with healthchecks)
Stop: `docker compose down` (data persists in `mysqldata` volume).

## Using the demo UI
1) Start the app (local `uvicorn` or `docker compose up --build`).
2) Open http://localhost:8000/ui/.
3) Click “Create” to generate a doc ID, then “Connect”.
4) Type in the editor; inserts/deletes stream over WebSocket and appear in the Event log.
5) To return later, paste the same doc ID and click “Connect”.

## Hitting the APIs directly
- Create doc: `POST /v1/docs`
- Snapshot: `GET /v1/docs/{doc_id}`
- WebSocket: `/v1/ws/docs/{doc_id}` (send `edit.insert`/`edit.delete`/`cursor.update`)
- Async jobs: `POST /v1/jobs`, `GET /v1/jobs/{id}`, exports at `POST /v1/docs/{doc_id}/export`
- Health/metrics: `/healthz`, `/readyz`, `/metrics`

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
