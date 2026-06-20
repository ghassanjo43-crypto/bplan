/* Tiny typed fetch wrapper around the FastAPI backend.
   The Vite dev server proxies /api -> http://127.0.0.1:8000 (see vite.config). */

// Accept either VITE_API_BASE or VITE_API_URL; default to the dev proxy path.
// Normalize so the value always ends in the backend's /api prefix.
const RAW = (import.meta.env.VITE_API_BASE ?? import.meta.env.VITE_API_URL ?? '/api').trim()
const BASE = /\/api\/?$/.test(RAW) ? RAW.replace(/\/$/, '') : RAW.replace(/\/$/, '') + '/api'

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(status: number, message: string, detail: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

const BACKEND_DOWN_HINT =
  'Cannot reach the API server. Make sure the backend is running: ' +
  'in backend/ run  py -m uvicorn app.main:app --reload  (it should be on http://127.0.0.1:8000).'

/** Notify the app that the session is gone (AuthProvider listens). */
function emitUnauthorized() {
  window.dispatchEvent(new CustomEvent('bp:unauthorized'))
}

// Bearer tokens. Cookies don't work when the frontend and API are on different
// domains (browsers block third-party cookies), so we keep tokens here and send
// them in the Authorization header. Cookies still work for same-origin setups.
const ACCESS_KEY = 'bp_access_token'
const REFRESH_KEY = 'bp_refresh_token'

export function setTokens(access?: string | null, refresh?: string | null) {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}
export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}
const getAccess = () => localStorage.getItem(ACCESS_KEY)
const getRefresh = () => localStorage.getItem(REFRESH_KEY)

async function rawFetch(method: string, path: string, body: unknown, signal: AbortSignal): Promise<Response> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const access = getAccess()
  if (access) headers['Authorization'] = `Bearer ${access}`
  return fetch(`${BASE}${path}`, {
    method,
    credentials: 'include', // send/receive HttpOnly auth cookies (same-origin)
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })
}

const NO_REFRESH = ['/auth/login', '/auth/refresh', '/auth/logout']

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  // Guard against a request that never settles (e.g. a dev-proxy connection
  // reset mid-response) — without this the UI can "spin forever".
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30_000)
  try {
    res = await rawFetch(method, path, body, controller.signal)
    // Access token expired: try a single silent refresh, then retry once.
    if (res.status === 401 && !NO_REFRESH.some((p) => path.startsWith(p))) {
      const refreshTok = getRefresh()
      const refreshed = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: refreshTok ? { Authorization: `Bearer ${refreshTok}` } : undefined,
      })
        .then(async (r) => {
          if (!r.ok) return false
          try {
            const data = await r.json()
            setTokens(data.access_token, data.refresh_token)
          } catch {
            /* no body — relying on refreshed cookies */
          }
          return true
        })
        .catch(() => false)
      if (refreshed) {
        res = await rawFetch(method, path, body, controller.signal)
      } else {
        clearTokens()
        emitUnauthorized()
      }
    }
  } catch (e) {
    if ((e as Error)?.name === 'AbortError') {
      throw new ApiError(0, 'The request timed out. It may have saved — refresh to check.', null)
    }
    // Network-level failure (DNS/connection refused) — backend almost certainly down.
    throw new ApiError(0, BACKEND_DOWN_HINT, null)
  } finally {
    clearTimeout(timeout)
  }

  if (!res.ok) {
    let detail: unknown = null
    try {
      detail = await res.json()
    } catch {
      /* non-JSON error body (e.g. dev-proxy error page when backend is down) */
    }
    const apiDetail = (detail as { detail?: unknown } | null)?.detail
    let message: string
    if (typeof apiDetail === 'string') {
      // A real, structured error from FastAPI.
      message = apiDetail
    } else if (Array.isArray(apiDetail)) {
      // FastAPI 422 validation errors: surface the offending field(s).
      message = apiDetail
        .map((e: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(e.loc) ? e.loc.filter((p) => p !== 'body').join('.') : ''
          return field ? `${field}: ${e.msg}` : e.msg
        })
        .filter(Boolean)
        .join('; ') || `Validation failed (${res.status})`
    } else if (res.status >= 500) {
      // 5xx with no JSON body = the Vite proxy couldn't reach the backend.
      message = `${BACKEND_DOWN_HINT} (HTTP ${res.status})`
    } else {
      message = `Request failed (${res.status})`
    }
    throw new ApiError(res.status, message, detail)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
}

export const API_BASE = BASE
