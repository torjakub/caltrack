import { and, eq, gt, inArray } from "drizzle-orm";
import { db } from "../client";
import {
  foodMicronutrients,
  foodNutrients,
  foods,
  logEntries,
  recipeItems,
  recipes,
  userProfile,
  userTargets,
} from "../schema";

export interface SyncChanges {
  user_profile: Record<string, unknown>[];
  user_targets: Record<string, unknown>[];
  foods: Record<string, unknown>[];
  food_nutrients: Record<string, unknown>[];
  food_micronutrients: Record<string, unknown>[];
  recipes: Record<string, unknown>[];
  log_entries: Record<string, unknown>[];
}

export function emptyChanges(): SyncChanges {
  return {
    user_profile: [],
    user_targets: [],
    foods: [],
    food_nutrients: [],
    food_micronutrients: [],
    recipes: [],
    log_entries: [],
  };
}

/** Only this user's own custom foods are ever pushed — cached external
 * foods are read-only mirrors of what the server already has (see
 * docs/architecture.md's lazy-cache design), so re-pushing them would be
 * both wasteful and pointless. */
async function dirtyCustomFoodIds(userId: string, since: string | null): Promise<string[]> {
  const condition = since
    ? and(eq(foods.isCustom, true), eq(foods.createdByUserId, userId), gt(foods.updatedAt, since))
    : and(eq(foods.isCustom, true), eq(foods.createdByUserId, userId));
  const rows = await db.select({ id: foods.id }).from(foods).where(condition);
  return rows.map((r) => r.id);
}

/** All of this user's own custom foods (not just recently-changed ones) —
 * needed so food_nutrients/food_micronutrients rows can be scoped correctly
 * regardless of which table actually changed. */
async function allCustomFoodIds(userId: string): Promise<string[]> {
  const rows = await db
    .select({ id: foods.id })
    .from(foods)
    .where(and(eq(foods.isCustom, true), eq(foods.createdByUserId, userId)));
  return rows.map((r) => r.id);
}

export async function collectDirtyChanges(userId: string, since: string | null): Promise<SyncChanges> {
  const changes = emptyChanges();

  const customFoodIds = await dirtyCustomFoodIds(userId, since);
  if (customFoodIds.length > 0) {
    const foodRows = await db.select().from(foods).where(inArray(foods.id, customFoodIds));
    changes.foods = foodRows.map((f) => ({
      id: f.id,
      source: f.source,
      source_id: f.sourceId,
      barcode: f.barcode,
      name: f.name,
      brand: f.brand,
      serving_size_g: f.servingSizeG,
      serving_unit_label: f.servingUnitLabel,
      image_url: f.imageUrl,
      is_custom: f.isCustom,
      created_by_user_id: f.createdByUserId,
      updated_at: f.updatedAt,
      deleted_at: f.deletedAt,
    }));
  }

  const allOwnFoodIds = await allCustomFoodIds(userId);
  if (allOwnFoodIds.length > 0) {
    const nutrientCondition = since
      ? and(inArray(foodNutrients.foodId, allOwnFoodIds), gt(foodNutrients.updatedAt, since))
      : inArray(foodNutrients.foodId, allOwnFoodIds);
    const nutrientRows = await db.select().from(foodNutrients).where(nutrientCondition);
    changes.food_nutrients = nutrientRows.map((n) => ({
      id: n.id,
      food_id: n.foodId,
      calories_kcal: n.caloriesKcal,
      protein_g: n.proteinG,
      carbs_g: n.carbsG,
      fat_g: n.fatG,
      updated_at: n.updatedAt,
      deleted_at: n.deletedAt,
    }));

    const microCondition = since
      ? and(inArray(foodMicronutrients.foodId, allOwnFoodIds), gt(foodMicronutrients.updatedAt, since))
      : inArray(foodMicronutrients.foodId, allOwnFoodIds);
    const microRows = await db.select().from(foodMicronutrients).where(microCondition);
    changes.food_micronutrients = microRows.map((m) => ({
      id: m.id,
      food_id: m.foodId,
      nutrient_code: m.nutrientCode,
      amount_per_100g: m.amountPer100g,
      updated_at: m.updatedAt,
      deleted_at: m.deletedAt,
    }));
  }

  const logCondition = since
    ? and(eq(logEntries.userId, userId), gt(logEntries.updatedAt, since))
    : eq(logEntries.userId, userId);
  const logRows = await db.select().from(logEntries).where(logCondition);
  changes.log_entries = logRows.map((e) => ({
    id: e.id,
    user_id: e.userId,
    food_id: e.foodId,
    recipe_id: e.recipeId,
    quantity_g: e.quantityG,
    quantity_servings: e.quantityServings,
    meal_type: e.mealType,
    logged_at: e.loggedAt,
    log_date: e.logDate,
    notes: e.notes,
    updated_at: e.updatedAt,
    deleted_at: e.deletedAt,
  }));

  // user_profile/user_targets/recipes: mobile doesn't create or edit these
  // yet (profile editing and recipe creation are web-only for now), so
  // there's never anything of ours to push — pulling them down still works
  // via applyServerChanges regardless.

  return changes;
}

async function upsertRow(
  table:
    | typeof foods
    | typeof foodNutrients
    | typeof foodMicronutrients
    | typeof userProfile
    | typeof userTargets
    | typeof recipes
    | typeof logEntries,
  id: string,
  values: Record<string, unknown>
): Promise<void> {
  const existing = await db.select().from(table as any).where(eq((table as any).id, id)).limit(1);
  if (existing.length > 0) {
    // Lost-update guard: if the local row is NEWER than the incoming server
    // row, an edit landed between the dirty-scan (which captured what we
    // just pushed) and this apply. Overwriting it here would silently drop
    // that edit — and it wouldn't even register as a conflict, because the
    // checkpoint advances either way. Keep local; it's still dirty and goes
    // out with the next push.
    const localUpdatedAt = (existing[0] as { updatedAt?: unknown }).updatedAt;
    const incomingAt = parseEpoch(values.updatedAt);
    const localAt = parseEpoch(localUpdatedAt);
    if (incomingAt !== null && localAt !== null && localAt > incomingAt) return;
    await db.update(table as any).set(values).where(eq((table as any).id, id));
  } else {
    await db.insert(table as any).values({ id, ...values });
  }
}

function parseEpoch(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? null : ms;
}

/** See the lost-update guard in upsertRow: true when the local row is newer
 * than the incoming server row and applying would silently drop local work. */
async function localRowNewer(
  table:
    | typeof foods
    | typeof foodNutrients
    | typeof foodMicronutrients
    | typeof userProfile
    | typeof userTargets
    | typeof recipes
    | typeof logEntries,
  id: string,
  incomingUpdatedAt: unknown
): Promise<boolean> {
  const rows = await db.select().from(table as any).where(eq((table as any).id, id)).limit(1);
  const localAt = parseEpoch((rows[0] as { updatedAt?: unknown } | undefined)?.updatedAt);
  const incomingAt = parseEpoch(incomingUpdatedAt);
  return localAt !== null && incomingAt !== null && localAt > incomingAt;
}

export async function applyServerChanges(serverChanges: SyncChanges): Promise<void> {
  for (const p of serverChanges.user_profile) {
    await upsertRow(userProfile, p.id as string, {
      userId: p.user_id,
      displayName: p.display_name,
      dateOfBirth: p.date_of_birth,
      sex: p.sex,
      heightCm: p.height_cm,
      weightKg: p.weight_kg,
      activityLevel: p.activity_level,
      goal: p.goal,
      weeklyGoalRateKg: p.weekly_goal_rate_kg,
      timezone: p.timezone,
      updatedAt: p.updated_at,
      deletedAt: p.deleted_at,
    });
  }

  for (const t of serverChanges.user_targets) {
    await upsertRow(userTargets, t.id as string, {
      userId: t.user_id,
      effectiveDate: t.effective_date,
      caloriesKcal: t.calories_kcal,
      proteinG: t.protein_g,
      carbsG: t.carbs_g,
      fatG: t.fat_g,
      fiberG: t.fiber_g,
      source: t.source,
      updatedAt: t.updated_at,
      deletedAt: t.deleted_at,
    });
  }

  for (const f of serverChanges.foods) {
    await upsertRow(foods, f.id as string, {
      source: f.source,
      sourceId: f.source_id,
      barcode: f.barcode,
      name: f.name,
      brand: f.brand,
      servingSizeG: f.serving_size_g,
      servingUnitLabel: f.serving_unit_label,
      imageUrl: f.image_url,
      isCustom: f.is_custom,
      createdByUserId: f.created_by_user_id,
      updatedAt: f.updated_at,
      deletedAt: f.deleted_at,
    });
  }

  for (const n of serverChanges.food_nutrients) {
    await upsertRow(foodNutrients, n.id as string, {
      foodId: n.food_id,
      caloriesKcal: n.calories_kcal,
      proteinG: n.protein_g,
      carbsG: n.carbs_g,
      fatG: n.fat_g,
      updatedAt: n.updated_at,
      deletedAt: n.deleted_at,
    });
  }

  for (const m of serverChanges.food_micronutrients) {
    await upsertRow(foodMicronutrients, m.id as string, {
      foodId: m.food_id,
      nutrientCode: m.nutrient_code,
      amountPer100g: m.amount_per_100g,
      updatedAt: m.updated_at,
      deletedAt: m.deleted_at,
    });
  }

  for (const r of serverChanges.recipes) {
    // Items sync as replace-all with their parent, so if we're keeping a
    // newer local recipe row, its items must be left untouched too.
    if (await localRowNewer(recipes, r.id as string, r.updated_at)) continue;
    await upsertRow(recipes, r.id as string, {
      userId: r.user_id,
      name: r.name,
      servings: r.servings,
      instructions: r.instructions,
      updatedAt: r.updated_at,
      deletedAt: r.deleted_at,
    });
    await db.delete(recipeItems).where(eq(recipeItems.recipeId, r.id as string));
    const items = (r.items as Record<string, unknown>[] | undefined) ?? [];
    for (const item of items) {
      await db.insert(recipeItems).values({
        id: item.id as string,
        recipeId: r.id as string,
        foodId: item.food_id as string,
        quantityG: item.quantity_g as number,
      });
    }
  }

  for (const e of serverChanges.log_entries) {
    await upsertRow(logEntries, e.id as string, {
      userId: e.user_id,
      foodId: e.food_id,
      recipeId: e.recipe_id,
      quantityG: e.quantity_g,
      quantityServings: e.quantity_servings,
      mealType: e.meal_type,
      loggedAt: e.logged_at,
      logDate: e.log_date,
      notes: e.notes,
      updatedAt: e.updated_at,
      deletedAt: e.deleted_at,
    });
  }
}

