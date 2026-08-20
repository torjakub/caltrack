import { apiFetch } from "./client";
import type { NutrientReferenceOut } from "./types";

export function getNutrientReference(): Promise<NutrientReferenceOut[]> {
  return apiFetch<NutrientReferenceOut[]>("/api/v1/nutrients/reference");
}
