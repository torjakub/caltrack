import { apiFetch } from "./client";
import type { TokenPair } from "./types";

export function setup(
  username: string,
  password: string,
  timezone: string,
  email?: string
): Promise<TokenPair> {
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

export function decodeUserIdFromToken(token: string): string {
  // JWT payload's `sub` claim is the user id (see server/app/core/security.py).
  const payload = token.split(".")[1];
  const json = JSON.parse(decodeAtob(payload));
  return json.sub;
}

function decodeAtob(base64url: string): string {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  return atob(padded);
}
