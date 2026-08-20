export type Sex = "male" | "female";
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type Goal = "lose" | "maintain" | "gain";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack";
export type FoodSource = "local" | "off" | "usda";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  username: string;
  email: string | null;
  role: string;
  is_active: boolean;
}

export interface UserProfileOut {
  id: string;
  user_id: string;
  display_name: string | null;
  date_of_birth: string | null;
  sex: Sex | null;
  height_cm: number | null;
  weight_kg: number | null;
  activity_level: ActivityLevel | null;
  goal: Goal | null;
  weekly_goal_rate_kg: number | null;
  timezone: string;
  updated_at: string;
}

export interface UserTargetsOut {
  id: string;
  user_id: string;
  effective_date: string;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number | null;
  source: "calculated" | "manual";
  updated_at: string;
}

export interface FoodNutrientsOut {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface FoodOut {
  id: string;
  source: FoodSource;
  barcode: string | null;
  name: string;
  brand: string | null;
  serving_size_g: number | null;
  serving_unit_label: string | null;
  image_url: string | null;
  is_custom: boolean;
  updated_at: string;
  nutrients: FoodNutrientsOut | null;
}

export interface LogEntryOut {
  id: string;
  food_id: string | null;
  recipe_id: string | null;
  quantity_g: number | null;
  quantity_servings: number | null;
  meal_type: MealType;
  logged_at: string;
  log_date: string;
  notes: string | null;
  updated_at: string;
  food: FoodOut | null;
}

export interface NutrientTotals {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface DailySummary {
  date: string;
  totals: NutrientTotals;
  targets: NutrientTotals | null;
  entries: LogEntryOut[];
}
