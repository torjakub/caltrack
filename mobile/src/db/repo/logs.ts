import { and, eq, isNull } from "drizzle-orm";
import { db } from "../client";
import { foodNutrients, logEntries } from "../schema";
import { newUuid } from "../../lib/uuid";
import { resolveLogDate } from "../../lib/dates";
import { getFoodLocal } from "./foods";
import type { LogEntryOut, MealType, NutrientTotals } from "../../api/types";

function nowIso(): string {
  return new Date().toISOString();
}

export interface LogEntryInput {
  foodId?: string;
  quantityG?: number;
  mealType: MealType;
  loggedAt: Date;
  notes?: string | null;
}

/** Always written locally first, regardless of connectivity — this is the
 * whole point of offline-first. Pushed to the server by the sync engine
 * (M4), not here. */
export async function createLogEntryLocal(input: LogEntryInput, userId: string, timezone: string): Promise<void> {
  const now = nowIso();
  await db.insert(logEntries).values({
    id: newUuid(),
    userId,
    foodId: input.foodId ?? null,
    quantityG: input.quantityG ?? null,
    mealType: input.mealType,
    loggedAt: input.loggedAt.toISOString(),
    logDate: resolveLogDate(input.loggedAt, timezone),
    notes: input.notes ?? null,
    updatedAt: now,
  });
}

export async function deleteLogEntryLocal(id: string): Promise<void> {
  const now = nowIso();
  await db.update(logEntries).set({ deletedAt: now, updatedAt: now }).where(eq(logEntries.id, id));
}

export async function listLogsForDate(userId: string, date: string): Promise<LogEntryOut[]> {
  const rows = await db
    .select()
    .from(logEntries)
    .where(and(eq(logEntries.userId, userId), eq(logEntries.logDate, date), isNull(logEntries.deletedAt)));

  const out: LogEntryOut[] = [];
  for (const row of rows) {
    const food = row.foodId ? await getFoodLocal(row.foodId) : null;
    out.push({
      id: row.id,
      food_id: row.foodId,
      recipe_id: row.recipeId,
      quantity_g: row.quantityG,
      quantity_servings: row.quantityServings,
      meal_type: row.mealType as MealType,
      logged_at: row.loggedAt,
      log_date: row.logDate,
      notes: row.notes,
      updated_at: row.updatedAt,
      food,
      recipe_name: null,
    });
  }
  return out.sort((a, b) => a.logged_at.localeCompare(b.logged_at));
}

export async function computeDailyTotals(entries: LogEntryOut[]): Promise<NutrientTotals> {
  const totals: NutrientTotals = { calories_kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 };
  for (const entry of entries) {
    if (entry.food_id && entry.quantity_g != null) {
      const [nutrients] = await db
        .select()
        .from(foodNutrients)
        .where(eq(foodNutrients.foodId, entry.food_id))
        .limit(1);
      if (nutrients) {
        const factor = entry.quantity_g / 100;
        totals.calories_kcal += nutrients.caloriesKcal * factor;
        totals.protein_g += nutrients.proteinG * factor;
        totals.carbs_g += nutrients.carbsG * factor;
        totals.fat_g += nutrients.fatG * factor;
      }
    }
  }
  return {
    calories_kcal: Math.round(totals.calories_kcal * 10) / 10,
    protein_g: Math.round(totals.protein_g * 10) / 10,
    carbs_g: Math.round(totals.carbs_g * 10) / 10,
    fat_g: Math.round(totals.fat_g * 10) / 10,
  };
}
