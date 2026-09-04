# Meridian Spine QMS — Base44 Dev Notes

## Stack
- FastAPI + Uvicorn + SQLAlchemy, Python 3.12.
- SQLite file DB (`meridian_qms.db`) — no external database service, no secrets.

## Running here
- `docker compose -f docker-compose.base44.yml up -d` — single `app` service.
- Base image `python:3.12-slim` with the repo bind-mounted at `/app`; deps install at startup.
- Startup command: `pip install -r requirements.txt && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app`.
- Host port 3000 → container 8000. Health path: `/`.

## Key behaviors
- **Seed runs on every container start** (`app/seed.py`): drops & recreates the schema, then inserts fixed traceability + CAPA + complaint data. DB is ephemeral to the container; restarts reseed.
- Frontend is a single static page at `/` (`app/static/index.html`) calling the JSON API.
- API surface: lots, components, devices, shipments, trace-back/trace-forward, CAPA workflow, complaints + MDR evaluation. See `app/main.py`.

## Verification
- `curl -sf http://localhost:3000/` returns the HTML page.
- `curl -sf http://localhost:3000/lots` returns seeded lot JSON.
- Live reload: editing files under `app/` triggers Uvicorn reload (no image rebuild needed).
