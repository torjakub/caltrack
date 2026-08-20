import { apiFetch } from "./client";
import type { RecipeOut } from "./types";

export interface RecipeItemInput {
  food_id: string;
  quantity_g: number;
}

export interface RecipeInput {
  name: string;
  servings: number;
  instructions?: string | null;
  items: RecipeItemInput[];
}

export function listRecipes(): Promise<RecipeOut[]> {
  return apiFetch<RecipeOut[]>("/api/v1/recipes");
}

export function getRecipe(id: string): Promise<RecipeOut> {
  return apiFetch<RecipeOut>(`/api/v1/recipes/${id}`);
}

export function createRecipe(payload: RecipeInput): Promise<RecipeOut> {
  return apiFetch<RecipeOut>("/api/v1/recipes", { method: "POST", body: JSON.stringify(payload) });
}

export function deleteRecipe(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/recipes/${id}`, { method: "DELETE" });
}
