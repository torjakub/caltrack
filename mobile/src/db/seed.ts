import { db } from "./client";
import { nutrientReference } from "./schema";

// Mirrors server/alembic/versions/ca33c81b75de_seed_nutrient_reference_data.py —
// keep these two lists in sync. Bundled with the app build rather than
// fetched, since it's static reference data (see docs/architecture.md).
const NUTRIENTS = [
  { code: "FIBTG", displayName: "Fiber", unit: "g", category: "macro" },
  { code: "SUGAR", displayName: "Sugars", unit: "g", category: "macro" },
  { code: "FASAT", displayName: "Saturated fat", unit: "g", category: "macro" },
  { code: "NA", displayName: "Sodium", unit: "mg", category: "mineral" },
  { code: "CHOLE", displayName: "Cholesterol", unit: "mg", category: "other" },
  { code: "K", displayName: "Potassium", unit: "mg", category: "mineral" },
  { code: "CA", displayName: "Calcium", unit: "mg", category: "mineral" },
  { code: "FE", displayName: "Iron", unit: "mg", category: "mineral" },
  { code: "VITC", displayName: "Vitamin C", unit: "mg", category: "vitamin" },
  { code: "VITD", displayName: "Vitamin D", unit: "mcg", category: "vitamin" },
  { code: "VITA", displayName: "Vitamin A", unit: "mcg", category: "vitamin" },
];

export async function seedNutrientReference(): Promise<void> {
  const existing = await db.select().from(nutrientReference).limit(1);
  if (existing.length > 0) return;
  await db.insert(nutrientReference).values(NUTRIENTS);
}
