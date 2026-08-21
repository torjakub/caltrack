import { sqliteTable, text, real, integer } from "drizzle-orm/sqlite-core";

// Single-row device/session config — not synced, mobile-only.
export const localMeta = sqliteTable("local_meta", {
  id: integer("id").primaryKey().default(1),
  deviceId: text("device_id").notNull(),
  userId: text("user_id"),
  serverBaseUrl: text("server_base_url"),
  timezone: text("timezone").notNull().default("UTC"),
  lastSyncedAt: text("last_synced_at"),
});

// --- Syncable tables (see docs/sync-protocol.md) ---
// updated_at/deleted_at on every row, client-generated UUID ids, mirroring
// the server schema exactly so sync (M4) is a straight diff.

export const userProfile = sqliteTable("user_profile", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  displayName: text("display_name"),
  dateOfBirth: text("date_of_birth"),
  sex: text("sex"),
  heightCm: real("height_cm"),
  weightKg: real("weight_kg"),
  activityLevel: text("activity_level"),
  goal: text("goal"),
  weeklyGoalRateKg: real("weekly_goal_rate_kg"),
  timezone: text("timezone").notNull().default("UTC"),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

export const userTargets = sqliteTable("user_targets", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  effectiveDate: text("effective_date").notNull(),
  caloriesKcal: real("calories_kcal").notNull(),
  proteinG: real("protein_g").notNull(),
  carbsG: real("carbs_g").notNull(),
  fatG: real("fat_g").notNull(),
  fiberG: real("fiber_g"),
  source: text("source").notNull(),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

// Not a full mirror of the server's foods cache — only this user's custom
// foods plus whatever's been searched/logged on this device (lazy cache).
export const foods = sqliteTable("foods", {
  id: text("id").primaryKey(),
  source: text("source").notNull(),
  sourceId: text("source_id"),
  barcode: text("barcode"),
  name: text("name").notNull(),
  brand: text("brand"),
  servingSizeG: real("serving_size_g"),
  servingUnitLabel: text("serving_unit_label"),
  imageUrl: text("image_url"),
  isCustom: integer("is_custom", { mode: "boolean" }).notNull().default(false),
  createdByUserId: text("created_by_user_id"),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

export const foodNutrients = sqliteTable("food_nutrients", {
  id: text("id").primaryKey(),
  foodId: text("food_id").notNull(),
  caloriesKcal: real("calories_kcal").notNull(),
  proteinG: real("protein_g").notNull(),
  carbsG: real("carbs_g").notNull(),
  fatG: real("fat_g").notNull(),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

export const foodMicronutrients = sqliteTable("food_micronutrients", {
  id: text("id").primaryKey(),
  foodId: text("food_id").notNull(),
  nutrientCode: text("nutrient_code").notNull(),
  amountPer100g: real("amount_per_100g").notNull(),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

// Static reference data bundled with the app build, not user-synced.
export const nutrientReference = sqliteTable("nutrient_reference", {
  code: text("code").primaryKey(),
  displayName: text("display_name").notNull(),
  unit: text("unit").notNull(),
  category: text("category").notNull(),
});

export const recipes = sqliteTable("recipes", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  name: text("name").notNull(),
  servings: real("servings").notNull().default(1),
  instructions: text("instructions"),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

export const recipeItems = sqliteTable("recipe_items", {
  id: text("id").primaryKey(),
  recipeId: text("recipe_id").notNull(),
  foodId: text("food_id").notNull(),
  quantityG: real("quantity_g").notNull(),
});

export const logEntries = sqliteTable("log_entries", {
  id: text("id").primaryKey(),
  userId: text("user_id").notNull(),
  foodId: text("food_id"),
  recipeId: text("recipe_id"),
  quantityG: real("quantity_g"),
  quantityServings: real("quantity_servings"),
  mealType: text("meal_type").notNull(),
  loggedAt: text("logged_at").notNull(),
  logDate: text("log_date").notNull(),
  notes: text("notes"),
  updatedAt: text("updated_at").notNull(),
  deletedAt: text("deleted_at"),
});

// Staging area for sync conflicts (M4) — populated by the sync engine,
// drained by the conflict-resolution screen.
export const syncConflicts = sqliteTable("sync_conflicts", {
  id: text("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  localVersionJson: text("local_version_json").notNull(),
  serverVersionJson: text("server_version_json").notNull(),
  createdAt: text("created_at").notNull(),
  resolved: integer("resolved", { mode: "boolean" }).notNull().default(false),
});
