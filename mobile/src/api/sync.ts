import { apiFetch } from "./client";
import type { SyncChanges } from "../db/repo/sync";

export interface SyncConflict {
  entity_type: string;
  id: string;
  mine: Record<string, unknown>;
  theirs: Record<string, unknown>;
}

export interface SyncResponse {
  synced_at: string;
  applied: Record<string, string[]>;
  conflicts: SyncConflict[];
  server_changes: SyncChanges;
}

export interface SyncRequestPayload {
  device_id: string;
  device_name: string | null;
  platform: "ios" | "android" | "web";
  since: string | null;
  changes: SyncChanges;
}

export function postSync(payload: SyncRequestPayload): Promise<SyncResponse> {
  return apiFetch<SyncResponse>("/api/v1/sync", { method: "POST", body: JSON.stringify(payload) });
}

export interface SyncResolution {
  entity_type: string;
  id: string;
  resolution: "mine" | "theirs" | "manual";
  record?: Record<string, unknown>;
}

export function postSyncResolve(deviceId: string, resolutions: SyncResolution[]): Promise<SyncResponse> {
  return apiFetch<SyncResponse>("/api/v1/sync/resolve", {
    method: "POST",
    body: JSON.stringify({ device_id: deviceId, resolutions }),
  });
}
