import { apiFetch } from "./client";
import type { UserProfileOut, UserTargetsOut } from "./types";

export type UserProfileUpdate = Omit<UserProfileOut, "id" | "user_id" | "updated_at">;

export function getProfile(): Promise<UserProfileOut> {
  return apiFetch<UserProfileOut>("/api/v1/profile");
}

export function updateProfile(payload: UserProfileUpdate): Promise<UserProfileOut> {
  return apiFetch<UserProfileOut>("/api/v1/profile", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getTargets(): Promise<UserTargetsOut> {
  return apiFetch<UserTargetsOut>("/api/v1/targets");
}

export function recalculateTargets(): Promise<UserTargetsOut> {
  return apiFetch<UserTargetsOut>("/api/v1/targets/recalculate", { method: "POST" });
}
