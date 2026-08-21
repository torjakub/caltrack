import { apiFetch, ApiError, getToken } from "./client";

export interface LLMStatus {
  provider: string;
  available: boolean;
}

export interface OCRNutritionResult {
  name: string | null;
  serving_size_g: number | null;
  calories_kcal: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  micronutrients: Record<string, number>;
}

export interface MealInsight {
  summary: string;
  positives: string[];
  concerns: string[];
  suggestions: string[];
}

export interface NutrientDeficiency {
  nutrient: string;
  gap_amount: number;
  unit: string;
  severity: string;
}

export interface FoodSuggestion {
  food: string;
  reason: string;
}

export interface PeriodAnalysis {
  summary: string;
  deficiencies: NutrientDeficiency[];
  suggestions: FoodSuggestion[];
}

export function getLlmStatus(): Promise<LLMStatus> {
  return apiFetch<LLMStatus>("/api/v1/llm/status");
}

export function mealReview(logEntryId: string): Promise<MealInsight> {
  return apiFetch<MealInsight>(`/api/v1/llm/meal-review/${logEntryId}`, { method: "POST" });
}

export function analysisDaily(date: string): Promise<PeriodAnalysis> {
  return apiFetch<PeriodAnalysis>(`/api/v1/llm/analysis/daily?date=${date}`, { method: "POST" });
}

export function analysisWeekly(start: string, end: string): Promise<PeriodAnalysis> {
  return apiFetch<PeriodAnalysis>(`/api/v1/llm/analysis/weekly?start=${start}&end=${end}`, { method: "POST" });
}

// Multipart upload isn't covered by apiFetch's JSON-only helper, so this
// builds the request directly (same base URL / auth / error handling).
export async function ocrNutritionLabel(imageFile: File | Blob): Promise<OCRNutritionResult> {
  const baseUrl =
    window.__CALTRACK_CONFIG__?.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const token = getToken();
  const form = new FormData();
  form.append("image", imageFile);

  const res = await fetch(`${baseUrl}/api/v1/llm/ocr-nutrition-label`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = typeof body.detail === "string" ? body.detail : body.detail?.message ?? message;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, message);
  }

  return res.json() as Promise<OCRNutritionResult>;
}
