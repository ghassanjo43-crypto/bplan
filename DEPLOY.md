# Deploying Business Plan Studio

The app ships as a **single web service**: FastAPI serves the built React SPA and
the `/api` backend from the same origin. One container, one URL.

- Frontend: React + Vite (built to `frontend/dist`)
- Backend: FastAPI + JSON storage, Word/PDF report generation
- Container: `Dockerfile` (multi-stage — builds the SPA, then a Python runtime
  with the WeasyPrint native libs needed for PDF reports)

There is **no separate backend URL** and **no Streamlit**. Whatever URL the host
gives you is the whole app.

---

## Option A — Render (Blueprint)

1. Push to GitHub (already done): `ghasn43/bplan`, branch `main`.
2. Render → **New → Blueprint** → pick this repo. It reads `render.yaml`
   (Docker web service, health check `/health`).
3. **Apply / Deploy**. First build takes a few minutes.
4. Open the service URL, e.g. `https://bplan-xxxx.onrender.com` — that's the full app.
   - Health: `GET /health` → `{"status":"ok"}`
   - API docs: `/docs`

### Render (manual Web Service)
New → **Web Service** → connect repo → **Runtime: Docker**,
**Dockerfile path: `./Dockerfile`** (leave build/start commands empty).

---

## Option B — Railway

New → **Deploy from GitHub repo** → select the repo. Railway detects the
`Dockerfile` and builds it. Generate a domain in the service settings.

---

## Option C — Run the container anywhere

```bash
docker build -t bplan .
docker run -p 8000:8000 bplan
# open http://localhost:8000
```

The platform's `$PORT` is honoured automatically; locally it defaults to `8000`.

---

## Configuration (env vars)

| Variable             | Default            | Purpose                                            |
|----------------------|--------------------|----------------------------------------------------|
| `PORT`               | `8000`             | Set by the host; the container binds it.           |
| `BP_SEED_ON_STARTUP` | `true`             | Seed a demo project on first boot.                 |
| `BP_DATA_DIR`        | `backend/data`     | JSON store location. Point at a mounted disk to persist. |
| `BP_CORS_ORIGINS`    | localhost dev URLs | Not needed in production (same-origin).             |

### Persisting data
The JSON store, uploaded images, and generated reports live on the container
filesystem, which is **ephemeral** on most hosts (resets on redeploy; the demo
re-seeds on boot). For durable data on Render, attach a disk and set
`BP_DATA_DIR=/data` (see the commented block in `render.yaml`; requires a paid plan).
**See the section below — this is the cause of "users/projects disappeared" and
"401 Not authenticated after a while" on the free tier.**

---

## Avoiding data loss & 401s after a restart (durable storage)

> Applies to whichever service runs the **API** (in the current split setup that
> is **`bplan2-api`**; the frontend `bplan2-frontend` only serves static files and
> calls the API via `VITE_API_BASE`).

### 1. The problem
On Render's **free tier the filesystem is ephemeral**:

- The API writes users, projects, and reports to **`data/`** on the container disk.
- When the free service **spins down after ~15 min idle (or on any redeploy)** and
  restarts, **`data/` is wiped**.
- On the next boot the app **re-seeds a fresh admin with a brand-new user id**
  (it only seeds when no admin exists), and any **users/projects you created are
  gone**.
- Your browser still holds an access/refresh **token whose `sub` is the *old*
  user id**, which no longer exists in the wiped store. The API can't resolve the
  user, so every protected call returns **`401 Not authenticated`** (the Admin
  → User Management list then shows "Could not load users", and you appear logged
  out). Logging out and back in mints a token for the *new* admin id — until the
  next restart.

> Note: the JWT signing secret itself is stable across restarts, so the 401 is
> **not** caused by secret rotation — it is caused by the **user record being
> wiped**, so the token's `sub` points at an id that no longer exists.

### 2. Recommended durable solution (pick one)

**Option A — Persistent disk (smallest change).** Attach a Render **persistent
disk** to the API service and point the JSON store at it:

- Add a disk (e.g. mount path `/data`, 1 GB) — *requires a paid instance type*.
- Set **`BP_DATA_DIR=/data`**.

Now `data/` survives restarts/redeploys: the admin keeps the **same user id**,
created users/projects persist, and existing tokens keep working. See the
commented `disk:` and `BP_DATA_DIR` block in `render.yaml`.

**Option B — A real database (most robust).** Move users/projects off the
filesystem entirely to **PostgreSQL** (or another managed DB). The storage layer
sits behind a `StorageBackend` interface, so a `PostgresStorage` implementation
can be added without touching the API/UI. This removes all filesystem-persistence
concerns and is the right choice for multi-instance / production scale.

### 3. Required Render environment variables

Set these on the **API service** (`bplan2-api`) so seeding, sessions and storage
are deterministic across restarts:

| Variable                  | Why it's needed                                                                 |
|---------------------------|---------------------------------------------------------------------------------|
| `ADMIN_EMAIL`             | The admin login email. Pinning it keeps the seeded admin identity predictable.  |
| `ADMIN_PASSWORD`          | The admin password (seeded on first boot when no admin exists). **Set a strong value; do not rely on the insecure `ChangeMe123!` default.** |
| `JWT_SECRET_KEY`          | Signs access tokens. Pin a strong random value so tokens are valid across restarts and not the shipped dev default. |
| `JWT_REFRESH_SECRET_KEY`  | Signs refresh tokens. Pin a strong random value (separate from the access secret). |
| `BP_DATA_DIR`             | **Only if using Option A** — set to the disk mount path (e.g. `/data`) so the JSON store is on the persistent disk. |

On the **frontend service** (`bplan2-frontend`), keep `VITE_API_BASE` (or
`VITE_API_URL`) set to the API origin, e.g. `https://bplan2-api.onrender.com`
(this is already configured and verified working).

### 4. Why code changes alone won't fix this
The 401s and disappearing data are a **storage-durability** problem, not an
application bug — the create/list logic already reads and writes the same store
correctly. **No change to the auth or storage code will keep data alive if the
underlying filesystem is wiped on restart.** Durability *only* comes from
persistent storage: a mounted disk (Option A) or an external database (Option B).
Until one of those is in place, expect data and sessions to reset whenever the
free-tier service restarts.

---

## Local development (unchanged)

Two processes:

```bash
# backend
cd backend && py -m uvicorn app.main:app --reload     # http://127.0.0.1:8000

# frontend (separate terminal)
cd frontend && npm run dev                            # http://localhost:5173
```

In dev, Vite proxies `/api` to the backend. The SPA-serving block in
`backend/app/main.py` is a no-op when `frontend/dist` is absent, so it doesn't
interfere with the Vite dev server.

## Notes
- First request after idle on free tiers can take ~30–60s (cold start).
- PDF reports need the WeasyPrint system libraries — already installed in the
  Dockerfile. If WeasyPrint is ever unavailable, the PDF route falls back to a
  styled, print-ready HTML file (Word generation is unaffected).
