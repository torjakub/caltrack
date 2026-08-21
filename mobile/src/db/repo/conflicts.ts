import { and, eq } from "drizzle-orm";
import { db } from "../client";
import { syncConflicts } from "../schema";
import { newUuid } from "../../lib/uuid";
import type { SyncConflict } from "../../api/sync";

function nowIso(): string {
  return new Date().toISOString();
}

export async function stageConflicts(conflicts: SyncConflict[]): Promise<void> {
  for (const c of conflicts) {
    // Avoid piling up duplicate staged conflicts if the same record fails
    // to sync more than once before the user resolves it.
    const existing = await db
      .select()
      .from(syncConflicts)
      .where(
        and(
          eq(syncConflicts.entityType, c.entity_type),
          eq(syncConflicts.entityId, c.id),
          eq(syncConflicts.resolved, false)
        )
      )
      .limit(1);
    if (existing.length > 0) {
      await db
        .update(syncConflicts)
        .set({ localVersionJson: JSON.stringify(c.mine), serverVersionJson: JSON.stringify(c.theirs) })
        .where(eq(syncConflicts.id, existing[0].id));
    } else {
      await db.insert(syncConflicts).values({
        id: newUuid(),
        entityType: c.entity_type,
        entityId: c.id,
        localVersionJson: JSON.stringify(c.mine),
        serverVersionJson: JSON.stringify(c.theirs),
        createdAt: nowIso(),
        resolved: false,
      });
    }
  }
}

export interface StagedConflict {
  id: string;
  entityType: string;
  entityId: string;
  mine: Record<string, unknown>;
  theirs: Record<string, unknown>;
  createdAt: string;
}

export async function listUnresolvedConflicts(): Promise<StagedConflict[]> {
  const rows = await db.select().from(syncConflicts).where(eq(syncConflicts.resolved, false));
  return rows.map((r) => ({
    id: r.id,
    entityType: r.entityType,
    entityId: r.entityId,
    mine: JSON.parse(r.localVersionJson),
    theirs: JSON.parse(r.serverVersionJson),
    createdAt: r.createdAt,
  }));
}

export async function markConflictResolved(id: string): Promise<void> {
  await db.update(syncConflicts).set({ resolved: true }).where(eq(syncConflicts.id, id));
}
