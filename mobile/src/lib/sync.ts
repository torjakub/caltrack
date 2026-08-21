import { eq } from "drizzle-orm";
import { Platform } from "react-native";
import * as Device from "expo-device";
import { db } from "../db/client";
import { localMeta } from "../db/schema";
import { useSessionStore } from "../store/session";
import { postSync } from "../api/sync";
import { collectDirtyChanges, applyServerChanges, emptyChanges } from "../db/repo/sync";
import { stageConflicts, markConflictResolved, type StagedConflict } from "../db/repo/conflicts";
import { postSyncResolve } from "../api/sync";

export interface SyncResult {
  ok: boolean;
  conflictCount: number;
  error?: string;
}

// Coalesce concurrent calls (e.g. a manual "Sync now" tap while the
// on-foreground auto-sync is already running) into a single in-flight sync.
let syncInFlight: Promise<SyncResult> | null = null;

export function runSync(): Promise<SyncResult> {
  if (!syncInFlight) {
    syncInFlight = doSync().finally(() => {
      syncInFlight = null;
    });
  }
  return syncInFlight;
}

async function doSync(): Promise<SyncResult> {
  const { userId, deviceId } = useSessionStore.getState();
  if (!userId) return { ok: false, conflictCount: 0, error: "Not logged in" };

  const [meta] = await db.select().from(localMeta).where(eq(localMeta.id, 1)).limit(1);
  const since = meta?.lastSyncedAt ?? null;

  try {
    const changes = await collectDirtyChanges(userId, since);
    const response = await postSync({
      device_id: deviceId,
      device_name: Device.deviceName,
      platform: Platform.OS === "ios" ? "ios" : "android",
      since,
      changes,
    });

    // Order matters: apply pulled data (so referenced foods exist) before
    // staging conflicts, and only advance the checkpoint once everything
    // has committed locally — a crash mid-sync should be safely retryable.
    await applyServerChanges(response.server_changes);

    if (response.conflicts.length > 0) {
      await stageConflicts(response.conflicts);
    }

    await db.update(localMeta).set({ lastSyncedAt: response.synced_at }).where(eq(localMeta.id, 1));

    return { ok: true, conflictCount: response.conflicts.length };
  } catch (err) {
    return { ok: false, conflictCount: 0, error: err instanceof Error ? err.message : "Sync failed" };
  }
}

/** Applies the winning record locally first (so it's no longer "dirty"
 * relative to the server and won't immediately re-trigger the same
 * conflict), tells the server which side won, marks the conflict resolved,
 * then runs a normal sync to reconcile the checkpoint — mirrors
 * docs/sync-protocol.md's resolution flow exactly. */
export async function resolveConflict(
  conflict: StagedConflict,
  resolution: "mine" | "theirs" | "manual",
  editedRecord?: Record<string, unknown>
): Promise<SyncResult> {
  const { deviceId } = useSessionStore.getState();
  const winner = resolution === "mine" ? conflict.mine : resolution === "manual" ? editedRecord! : conflict.theirs;

  const changes = emptyChanges();
  (changes[conflict.entityType as keyof typeof changes] as Record<string, unknown>[]).push(winner);
  await applyServerChanges(changes);

  await postSyncResolve(deviceId, [
    {
      entity_type: conflict.entityType,
      id: conflict.entityId,
      resolution,
      record: resolution === "theirs" ? undefined : winner,
    },
  ]);

  await markConflictResolved(conflict.id);

  return runSync();
}
