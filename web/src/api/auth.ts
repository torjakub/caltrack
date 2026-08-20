import { apiFetch } from "./client";
import type { TokenPair, UserOut } from "./types";

export function setup(username: string, password: string, email?: string): Promise<TokenPair> {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  return apiFetch<TokenPair>("/api/v1/auth/setup", {
    method: "POST",
    body: JSON.stringify({ username, password, email: email || null, timezone }),
  });
}

export function login(username: string, password: string): Promise<TokenPair> {
  return apiFetch<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function me(): Promise<UserOut> {
  return apiFetch<UserOut>("/api/v1/auth/me");
}
