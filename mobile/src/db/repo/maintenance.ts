import { eq } from "drizzle-orm";
import { db } from "../client";
import {
  foodMicronutrients,
  foodNutrients,
  foods,
  localMeta,
  logEntries,
  recipeItems,
  recipes,
  syncConflicts,
} from "../schema";

/** Wipes all locally-cached food/log/recipe/conflict data and resets the
 * sync checkpoint, while keeping the device logged in (profile/session
 * untouched). The next sync does a full fresh pull of whatever legitimately
 * belongs to the current account. Meant for recovering from a corrupted or
 * cross-account-contaminated local cache (see docs/sync-protocol.md) — not
 * a normal user action. */
export async function resetLocalData(): Promise<void> {
  await db.delete(logEntries);
  await db.delete(recipeItems);
  await db.delete(recipes);
  await db.delete(foodMicronutrients);
  await db.delete(foodNutrients);
  await db.delete(foods);
  await db.delete(syncConflicts);
  await db.update(localMeta).set({ lastSyncedAt: null }).where(eq(localMeta.id, 1));
}
