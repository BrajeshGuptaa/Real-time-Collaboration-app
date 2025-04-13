Real-Time Collaboration Backend (Google Docs–style)

Overview
- FastAPI server with WebSocket for live ops and presence
- Minimal CRDT (Logoot/LSEQ-like) for text inserts/deletes
- Postgres (documents, ops) and Redis (presence/pubsub) scaffolding
- Health/ready endpoints and basic configuration via environment

Quick Start
1) Install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
2) Start infra (optional): `docker compose up -d` (MySQL + Redis)
3) Run API: `PYTHONPATH=app/src uvicorn rt_collab.main:app --reload`
4) Open docs: http://localhost:8000/docs

Environment
- `DATABASE_URL` (async): e.g. `mysql+aiomysql://brajesh350194:Beast%405uuu@localhost:3306/rt_collab`
- `REDIS_URL`: default redis://localhost:6379/0
- `ALLOWED_ORIGINS`: comma-separated; default http://localhost:3000

Endpoints
- REST
  - POST /v1/docs             → create document
  - GET  /v1/docs/{doc_id}    → fetch snapshot text and version
  - GET  /healthz, /readyz    → health checks
- WebSocket
  - /v1/ws/docs/{doc_id}
    - Client → server: op.submit, cursor.update
    - Server → client: op.broadcast, presence.sync, ack/nack

Notes
- If your MySQL password contains special characters, URL-encode them (e.g., `@` → `%40`).
- CRDT is a compact Logoot-like sequence with positional identifiers; suitable for demo and tests.
- Persistence is scaffolded with SQLAlchemy; defaults now target MySQL (async via aiomysql). Add Alembic/migrations for production.
- Presence uses in-memory manager by default; Redis is supported and configured in docker-compose.




### Suggested Next Steps

Ship persistence and auth end-to-end, backed by automated tests.
Build multi-user UI features (presence indicators, version history, comments).
Add deployment/observability infrastructure (Docker images, k8s manifests, metrics dashboards, alerts).
Document architecture, scaling assumptions, and testing strategy to make the project review-ready.