import { and, desc, eq, isNull, like, or } from "drizzle-orm";
import { db } from "../client";
import { foodMicronutrients, foodNutrients, foods } from "../schema";
import { newUuid } from "../../lib/uuid";
import type { FoodOut } from "../../api/types";

function nowIso(): string {
  return new Date().toISOString();
}

export async function searchFoodsLocal(query: string, limit = 25): Promise<FoodOut[]> {
  const like_ = `%${query}%`;
  const rows = await db
    .select()
    .from(foods)
    .where(and(isNull(foods.deletedAt), or(like(foods.name, like_), like(foods.brand, like_))))
    .orderBy(desc(foods.isCustom), foods.name)
    .limit(limit);
  return Promise.all(rows.map((f) => hydrateFood(f.id, f)));
}

export async function getFoodByBarcodeLocal(barcode: string): Promise<FoodOut | null> {
  const rows = await db
    .select()
    .from(foods)
    .where(and(eq(foods.barcode, barcode), isNull(foods.deletedAt)))
    .orderBy(desc(foods.isCustom))
    .limit(1);
  if (rows.length === 0) return null;
  return hydrateFood(rows[0].id, rows[0]);
}

export async function getFoodLocal(foodId: string): Promise<FoodOut | null> {
  const rows = await db.select().from(foods).where(eq(foods.id, foodId)).limit(1);
  if (rows.length === 0) return null;
  return hydrateFood(foodId, rows[0]);
}

async function hydrateFood(foodId: string, row: typeof foods.$inferSelect): Promise<FoodOut> {
  const [nutrients] = await db.select().from(foodNutrients).where(eq(foodNutrients.foodId, foodId)).limit(1);
  const micros = await db.select().from(foodMicronutrients).where(eq(foodMicronutrients.foodId, foodId));
  return {
    id: row.id,
    source: row.source as FoodOut["source"],
    barcode: row.barcode,
    name: row.name,
    brand: row.brand,
    serving_size_g: row.servingSizeG,
    serving_unit_label: row.servingUnitLabel,
    image_url: row.imageUrl,
    is_custom: row.isCustom,
    updated_at: row.updatedAt,
    nutrients: nutrients
      ? {
          calories_kcal: nutrients.caloriesKcal,
          protein_g: nutrients.proteinG,
          carbs_g: nutrients.carbsG,
          fat_g: nutrients.fatG,
        }
      : null,
    micronutrients: micros.map((m) => ({ nutrient_code: m.nutrientCode, amount_per_100g: m.amountPer100g })),
  };
}

/** Upserts a food fetched from the server into the local cache (see the
 * lazy-cache design in docs/architecture.md — mobile only mirrors foods
 * it's actually seen, not the server's whole external cache). */
export async function cacheRemoteFood(remote: FoodOut): Promise<void> {
  const now = nowIso();
  await db
    .insert(foods)
    .values({
      id: remote.id,
      source: remote.source,
      barcode: remote.barcode,
      name: remote.name,
      brand: remote.brand,
      servingSizeG: remote.serving_size_g,
      servingUnitLabel: remote.serving_unit_label,
      imageUrl: remote.image_url,
      isCustom: remote.is_custom,
      updatedAt: remote.updated_at,
    })
    .onConflictDoUpdate({
      target: foods.id,
      set: {
        name: remote.name,
        brand: remote.brand,
        servingSizeG: remote.serving_size_g,
        servingUnitLabel: remote.serving_unit_label,
        imageUrl: remote.image_url,
        updatedAt: remote.updated_at,
      },
    });

  if (remote.nutrients) {
    const existing = await db.select().from(foodNutrients).where(eq(foodNutrients.foodId, remote.id)).limit(1);
    if (existing.length > 0) {
      await db
        .update(foodNutrients)
        .set({ ...toNutrientRow(remote.nutrients), updatedAt: now })
        .where(eq(foodNutrients.foodId, remote.id));
    } else {
      await db.insert(foodNutrients).values({
        id: newUuid(),
        foodId: remote.id,
        ...toNutrientRow(remote.nutrients),
        updatedAt: now,
      });
    }
  }

  for (const micro of remote.micronutrients) {
    const existing = await db
      .select()
      .from(foodMicronutrients)
      .where(and(eq(foodMicronutrients.foodId, remote.id), eq(foodMicronutrients.nutrientCode, micro.nutrient_code)))
      .limit(1);
    if (existing.length > 0) {
      await db
        .update(foodMicronutrients)
        .set({ amountPer100g: micro.amount_per_100g, updatedAt: now })
        .where(eq(foodMicronutrients.id, existing[0].id));
    } else {
      await db.insert(foodMicronutrients).values({
        id: newUuid(),
        foodId: remote.id,
        nutrientCode: micro.nutrient_code,
        amountPer100g: micro.amount_per_100g,
        updatedAt: now,
      });
    }
  }
}

function toNutrientRow(n: NonNullable<FoodOut["nutrients"]>) {
  return { caloriesKcal: n.calories_kcal, proteinG: n.protein_g, carbsG: n.carbs_g, fatG: n.fat_g };
}

export interface CustomFoodInput {
  name: string;
  servingSizeG?: number | null;
  caloriesKcal: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
}

/** Custom foods are created purely locally in M3 — no server round trip.
 * They push to the server once the sync engine (M4) exists. */
export async function createCustomFoodLocal(input: CustomFoodInput, userId: string): Promise<FoodOut> {
  const now = nowIso();
  const id = newUuid();
  await db.insert(foods).values({
    id,
    source: "local",
    name: input.name,
    servingSizeG: input.servingSizeG ?? null,
    isCustom: true,
    createdByUserId: userId,
    updatedAt: now,
  });
  await db.insert(foodNutrients).values({
    id: newUuid(),
    foodId: id,
    caloriesKcal: input.caloriesKcal,
    proteinG: input.proteinG,
    carbsG: input.carbsG,
    fatG: input.fatG,
    updatedAt: now,
  });
  return getFoodLocal(id) as Promise<FoodOut>;
}
