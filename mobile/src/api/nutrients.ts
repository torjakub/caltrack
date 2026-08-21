import { apiFetch } from "./client";

export interface NutrientReferenceOut {
  code: string;
  display_name: string;
  unit: string;
  category: string;
}

export function getNutrientReferenceRemote(): Promise<NutrientReferenceOut[]> {
  return apiFetch<NutrientReferenceOut[]>("/api/v1/nutrients/reference");
}
