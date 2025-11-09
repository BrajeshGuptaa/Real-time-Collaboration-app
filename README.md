Real-Time Collaboration Backend

A FastAPI service that supports Google Docs–style collaboration with live CRDT ops, a WebSocket channel for presence, and a tiny demo UI served from `/ui`.

## Stack
- FastAPI + WebSockets for HTTP and realtime
- Logoot/LSEQ-like CRDT for text inserts/deletes
- MySQL (documents/ops) and Redis (presence/pubsub) via docker compose
- SQLAlchemy (async), Pydantic settings, CORS enabled

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

## Testing
```bash
cd app
source .venv/bin/activate
pytest
```
