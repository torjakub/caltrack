import { apiFetch } from "./client";
import type { FoodOut } from "./types";

export function searchFoods(query: string): Promise<FoodOut[]> {
  return apiFetch<FoodOut[]>(`/api/v1/foods/search?q=${encodeURIComponent(query)}`);
}

export function lookupBarcode(barcode: string): Promise<FoodOut> {
  return apiFetch<FoodOut>(`/api/v1/foods/barcode/${encodeURIComponent(barcode)}`);
}

export interface CustomFoodInput {
  name: string;
  brand?: string | null;
  serving_size_g?: number | null;
  serving_unit_label?: string | null;
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export function createCustomFood(payload: CustomFoodInput): Promise<FoodOut> {
  return apiFetch<FoodOut>("/api/v1/foods", { method: "POST", body: JSON.stringify(payload) });
}
