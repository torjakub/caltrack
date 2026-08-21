import { apiFetch } from "./client";
import type { RecipeOut } from "./types";

export function listRecipesRemote(): Promise<RecipeOut[]> {
  return apiFetch<RecipeOut[]>("/api/v1/recipes");
}
