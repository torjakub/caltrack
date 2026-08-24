import * as SecureStore from "expo-secure-store";
import { useSessionStore } from "../store/session";

const TOKEN_KEY = "caltrack_access_token";
const REFRESH_TOKEN_KEY = "caltrack_refresh_token";

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function setToken(token: string | null): Promise<void> {
  if (token) await SecureStore.setItemAsync(TOKEN_KEY, token);
  else await SecureStore.deleteItemAsync(TOKEN_KEY);
}

export async function setRefreshToken(token: string | null): Promise<void> {
  if (token) await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
  else await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class NoServerConfiguredError extends Error {}

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

// Endpoints whose own 401 IS the answer (bad credentials, expired refresh
// token) — never attempt a refresh-retry for these.
const AUTH_PATHS = ["/api/v1/auth/login", "/api/v1/auth/setup", "/api/v1/auth/refresh"];

let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(baseUrl: string): Promise<boolean> {
  // Single-flight: concurrent 401s share one refresh call.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const refreshToken = await getRefreshToken();
      if (!refreshToken) return false;
      try {
        const res = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return false;
        const pair = (await res.json()) as { access_token: string; refresh_token: string };
        await setToken(pair.access_token);
        await setRefreshToken(pair.refresh_token);
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
  const baseUrl = useSessionStore.getState().serverBaseUrl;
  if (!baseUrl) throw new NoServerConfiguredError("No server configured");

  const send = async (): Promise<Response> => {
    const token = await getToken();
    const headers: Record<string, string> = {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers as Record<string, string> | undefined),
    };
    return fetch(`${baseUrl}${path}`, { ...options, headers });
  };

  let res = await send();

  // A 401 on an authenticated request usually means the access token simply
  // expired — try one refresh-and-retry before giving up and logging out.
  if (
    res.status === 401 &&
    !retriedAfterRefresh &&
    !AUTH_PATHS.some((p) => path.startsWith(p)) &&
    (await refreshTokens(baseUrl))
  ) {
    res = await send();
  }

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      const body = await res.json();
      detail = body.detail;
    } catch {
      // response body wasn't JSON
    }

    // Refresh failed too (or wasn't possible): the stored session is
    // unrecoverable — log out locally so the app recovers to the login
    // screen instead of surfacing a raw error on every subsequent call.
    if (res.status === 401) {
      await setRefreshToken(null);
      await useSessionStore.getState().logout();
    }

    throw new ApiError(res.status, formatErrorDetail(detail, res.statusText));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
