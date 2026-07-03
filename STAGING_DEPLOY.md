# Staging deployment — Revenue Stream Wizard

Stands up an **isolated** staging environment on Render for the
`feature/revenue-stream-wizard` branch, **mirroring production's split**:

| Role | Staging service | Type | Mirrors |
|------|-----------------|------|---------|
| API  | `bplan-staging-api` | Web Service (Docker) | `bplan2-api` |
| UI   | `bplan-staging-frontend` | Static Site | `bplan2-frontend` |

> **Isolation guarantees.** Staging uses **new** service names, its **own**
> data/disk, its **own** JWT secrets, and **staging-only** admin credentials. It
> never reads or writes production data and never changes the production
> `bplan2-*` services or their env vars. Production keeps deploying from `main`;
> staging deploys from `feature/revenue-stream-wizard`.

The repo `Dockerfile` builds one full-stack image (FastAPI + built SPA). We run
that image as the **API** service, and build the frontend separately as a
**Static Site** that points at the staging API via `VITE_API_BASE` — exactly
how production is arranged.

---

## 1. Environment variables

### `bplan-staging-api` (Web Service · Docker)

| Variable | Value (staging) | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | **new random** (staging-only) | **Never** reuse the production secret. |
| `JWT_REFRESH_SECRET_KEY` | **new random** (staging-only) | Separate from the access secret. |
| `ADMIN_EMAIL` | e.g. `staging-admin@yourdomain.com` | **Staging-only** — not the production admin. |
| `ADMIN_PASSWORD` | a strong **staging-only** password | Seeded on first boot when no admin exists. |
| `BP_SEED_ON_STARTUP` | `true` | Loads the demo so staging is explorable. |
| `BP_CORS_ORIGINS` | `https://bplan-staging-frontend.onrender.com` | The **staging frontend** URL (see §3). |
| `BP_COOKIE_SECURE` | `true` | HTTPS. |
| `BP_COOKIE_SAMESITE` | `none` | Cross-domain frontend↔API. |
| `BP_STORAGE_BACKEND` | `json` | Only backend implemented today. |
| `BP_DATA_DIR` | `/data` | **Only if** you attach a disk (see §4); omit otherwise. |
| `BP_SEED_DEV_USERS` | `false` | No demo finance user (optional). |
| `BP_ADMIN_RESET` | `false` | Set `true` for one deploy only if you need to reset the staging admin. |
| `PORT` | *(set by Render)* | Do not set manually. |

### `bplan-staging-frontend` (Static Site)

| Variable | Value (staging) | Notes |
|---|---|---|
| `VITE_API_BASE` | `https://bplan-staging-api.onrender.com` | **Build-time** — the staging API origin (see §2). |

> Render assigns the real hostnames when the services are created. If they differ
> from the names above, use the **actual** URLs Render shows and update
> `VITE_API_BASE` and `BP_CORS_ORIGINS` to match, then redeploy.

---

## 2. Staging frontend `VITE_API_BASE`
```
VITE_API_BASE = https://bplan-staging-api.onrender.com
```
This is baked in **at build time**, so after you set/change it you must
**redeploy the static site**. Point it at the **staging** API only — never the
production `bplan2-api`.

## 3. Staging API `BP_CORS_ORIGINS`
```
BP_CORS_ORIGINS = https://bplan-staging-frontend.onrender.com
```
Only the staging frontend origin. Do **not** add the production frontend here.

## 4. Persistent disk & `BP_DATA_DIR`
- **Recommended:** attach a **persistent disk** to `bplan-staging-api` (mount
  path `/data`, ~1 GB) and set **`BP_DATA_DIR=/data`**. This keeps staging data
  (and the seeded admin id → stable sessions) across restarts and **fully
  separate** from production. Render disks require a **paid** instance type.
- **Without a disk (free tier):** **omit `BP_DATA_DIR`** (it defaults to the
  container's `backend/data`, which is **ephemeral** and resets on restart).
  Fine for a throwaway demo, but data/sessions won't persist.
- **Never** point `BP_DATA_DIR` at anything shared with production.

## 5. Staging admin credentials (staging-only)
```
ADMIN_EMAIL    = staging-admin@yourdomain.com     # not the production admin
ADMIN_PASSWORD = <a strong staging-only password>  # not the production password
```
Set these in the `bplan-staging-api` dashboard env. If the datastore is wiped and
you need to reset the admin, set `BP_ADMIN_RESET=true`, deploy once, then set it
back to `false` (safe — it only touches the admin user).

---

## 6. Exact Render dashboard steps

### A. Create the staging API (`bplan-staging-api`)
1. Render → **New → Web Service** → connect the `ghassanjo43-crypto/bplan` repo.
2. **Branch:** `feature/revenue-stream-wizard`.
3. **Runtime:** Docker · **Dockerfile path:** `./Dockerfile` (leave build/start commands empty — the Dockerfile's `CMD` honours `$PORT`).
4. **Name:** `bplan-staging-api`.
5. **Health Check Path:** `/health`.
6. **Environment:** add every variable from the §1 API table (generate fresh JWT secrets; set a staging-only `ADMIN_PASSWORD`).
7. *(Recommended)* **Advanced → Add Disk:** name `bplan-staging-data`, mount path `/data`, size 1 GB, and set `BP_DATA_DIR=/data`.
8. **Create Web Service.** Note the URL it gives you, e.g. `https://bplan-staging-api.onrender.com`.

### B. Create the staging frontend (`bplan-staging-frontend`)
1. Render → **New → Static Site** → same repo.
2. **Branch:** `feature/revenue-stream-wizard`.
3. **Build Command:** `cd frontend && npm ci && npm run build`.
4. **Publish Directory:** `frontend/dist`.
5. **Name:** `bplan-staging-frontend`.
6. **Environment:** `VITE_API_BASE = https://bplan-staging-api.onrender.com` (the URL from step A.8).
7. **Redirects/Rewrites:** add a rule **Source `/*` → Destination `/index.html`** (type **Rewrite**) so the SPA routes work.
8. **Create Static Site.** Note its URL, e.g. `https://bplan-staging-frontend.onrender.com`.

### C. Reconcile the URLs
1. If the real URLs differ from the placeholders, update **`VITE_API_BASE`**
   (frontend) and **`BP_CORS_ORIGINS`** (API) to the actual values.
2. **Redeploy the static site** (so the new `VITE_API_BASE` is baked in) and
   restart the API.

### D. Verify
- `GET https://bplan-staging-api.onrender.com/health` → `200`.
- Open the staging frontend, log in with the **staging** admin, go to
  **Revenue → Revenue Setup**, and use **+ Add Revenue Stream**.

---

## 7. Guardrails checklist
- [ ] New names `bplan-staging-*` (never edit `bplan2-api` / `bplan2-frontend`).
- [ ] Branch is `feature/revenue-stream-wizard` (production stays on `main`).
- [ ] **Fresh** `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` (not production's).
- [ ] **Staging-only** `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
- [ ] `BP_DATA_DIR` / disk is **separate** from production (or omitted).
- [ ] `BP_CORS_ORIGINS` and `VITE_API_BASE` reference **only** staging URLs.
- [ ] Production Render env vars are **unchanged**.

> A reference Blueprint is provided in `render.staging.yaml`. It is **not**
> auto-applied (Render only syncs the default `render.yaml`) and does **not**
> touch production — treat it as a template if you prefer Blueprint-based setup;
> otherwise use the dashboard steps above.
