# Business Plan Projection — Backend

FastAPI + Pydantic backend that captures every assumption required to build a
complete financial projection. Persistence is JSON-file based today, behind a
`StorageBackend` interface designed for a drop-in PostgreSQL upgrade.

## Requirements

- Python 3.10+ (tested on 3.14)

## Setup

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

- API root: `http://127.0.0.1:8000/api`
- Interactive docs (Swagger): `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

A demo project (**Acme SaaS — Demo Plan**) is seeded automatically on first run.

## Configuration (environment variables)

| Variable             | Default               | Description                                  |
| -------------------- | --------------------- | -------------------------------------------- |
| `BP_STORAGE_BACKEND` | `json`                | Storage backend (`json`; `postgres` planned) |
| `BP_DATA_DIR`        | `backend/data`        | Where JSON project files are written         |
| `BP_CORS_ORIGINS`    | Vite dev URLs         | Comma-separated allowed origins              |
| `BP_SEED_ON_STARTUP` | `true`                | Seed a demo project when the store is empty  |

### Administrator credential lifecycle

`ADMIN_EMAIL` and `ADMIN_PASSWORD` are bootstrap inputs only: on startup they
create the first administrator when no administrator record exists. The saved
user record (including its bcrypt password hash) is authoritative after that;
changing `ADMIN_PASSWORD` does not change an existing administrator password.
Administrators should normally use **Admin / Account / Security** in Planora.

`BP_ADMIN_RESET=true` remains an explicit, one-deployment emergency recovery
mechanism. It replaces the database-backed credential from `ADMIN_PASSWORD` and
must immediately be returned to `false`; it is not a second runtime password.
Admin resets of normal users generate a random temporary password on the server,
show it once, revoke the user's prior JWT sessions, and require a permanent
password before any non-auth API route is available.

## Project structure

```
backend/app/
  main.py            # FastAPI app, CORS, lifespan seeding, router wiring
  config.py          # env-driven settings
  models/            # Pydantic domain models (one file per topic group)
  schemas/           # request-only schemas (e.g. ProjectCreate)
  routes/            # project routes + generated section routers
  services/          # registry, project service, completion/review, seed
  storage/           # StorageBackend interface + JSONStorage implementation
  utils/             # id + timestamp helpers
```

## API surface

Project-level:

```
GET    /api/projects
POST   /api/projects                      { "name": "..." }
GET    /api/projects/{id}
PUT    /api/projects/{id}                  full document
DELETE /api/projects/{id}
GET    /api/projects/{id}/completion
GET    /api/projects/{id}/review
GET    /api/projects/{id}/export-json
```

Singleton sections (`GET` / `PUT`): `setup`, `working-capital`, `financing`,
`tax`, `kpis`.

Collection sections (`GET` / `POST` / `PUT {item_id}` / `DELETE {item_id}`):
`products`, `revenue`, `direct-costs`, `staffing`, `operating-expenses`,
`startup-costs`, `fixed-assets`, `scenarios`.

All section routers are generated from a single registry
(`app/services/registry.py`) — add a new section by adding one `SectionSpec`
plus a model.

## Upgrade path to PostgreSQL

The service layer depends only on `app/storage/base.py::StorageBackend`. To
migrate, implement a `PostgresStorage` with the same five methods and register
it in `app/storage/__init__.py`. The aggregate document shape maps cleanly onto
one table per list-section.
