import * as SecureStore from "expo-secure-store";
import { useSessionStore } from "../store/session";

const TOKEN_KEY = "caltrack_access_token";

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function setToken(token: string | null): Promise<void> {
  if (token) await SecureStore.setItemAsync(TOKEN_KEY, token);
  else await SecureStore.deleteItemAsync(TOKEN_KEY);
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

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = useSessionStore.getState().serverBaseUrl;
  if (!baseUrl) throw new NoServerConfiguredError("No server configured");

  const token = await getToken();
  const headers: Record<string, string> = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(`${baseUrl}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail: unknown = undefined;
    try {
      const body = await res.json();
      detail = body.detail;
    } catch {
      // response body wasn't JSON
    }

    // A 401 on an authenticated request means the stored token is invalid
    // or expired (e.g. the server's database was reset, or the token
    // simply expired) — log out locally so the app recovers to the login
    // screen instead of surfacing a raw error on every subsequent call.
    if (res.status === 401) {
      await useSessionStore.getState().logout();
    }

    throw new ApiError(res.status, formatErrorDetail(detail, res.statusText));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
