declare global {
  interface Window {
    __CALTRACK_CONFIG__?: { API_BASE_URL?: string };
  }
}

const API_BASE_URL =
  window.__CALTRACK_CONFIG__?.API_BASE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

const TOKEN_KEY = "caltrack_access_token";
const REFRESH_TOKEN_KEY = "caltrack_refresh_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// FastAPI's `detail` is a plain string for most errors, but for 422
// validation failures it's an array of {loc, msg, type} objects — render
// either shape as one readable string instead of "[object Object]".
function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item ? String((item as { msg: unknown }).msg) : String(item)
      )
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return fallback;
}

// Endpoints whose own 401/403 IS the answer (bad credentials, expired
// refresh token) — never attempt a refresh-retry for these.
const AUTH_PATHS = ["/api/v1/auth/login", "/api/v1/auth/setup", "/api/v1/auth/refresh"];

let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  // Single-flight: concurrent 401s share one refresh call. The loser of a
  // race re-reads the stored tokens, so a stale retry still gets the new pair.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = getRefreshToken();
      if (!refreshToken) return false;
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          setToken(null);
          setRefreshToken(null);
          return false;
        }
        const pair = (await res.json()) as { access_token: string; refresh_token: string };
        setToken(pair.access_token);
        setRefreshToken(pair.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retriedAfterRefresh = false
): Promise<T> {
  const send = async (): Promise<Response> => {
    const token = getToken();
    const headers: Record<string, string> = {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined),
    };
    return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  };

  let res = await send();

  if (
    res.status === 401 &&
    !retriedAfterRefresh &&
    !AUTH_PATHS.some((p) => path.startsWith(p)) &&
    (await refreshTokens())
  ) {
    res = await send();
  }

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      const body = await res.json();
      detail = body.detail;
    } catch {
      // response body wasn't JSON — keep statusText
    }
    throw new ApiError(res.status, formatErrorDetail(detail, res.statusText));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
