import { apiFetch } from "./client";
import type { DailySummary, LogEntryOut, MealType } from "./types";

export interface LogEntryInput {
  food_id?: string | null;
  recipe_id?: string | null;
  quantity_g?: number | null;
  quantity_servings?: number | null;
  meal_type: MealType;
  logged_at: string;
  notes?: string | null;
}

export function getDailySummary(date: string): Promise<DailySummary> {
  return apiFetch<DailySummary>(`/api/v1/logs/summary?date=${date}`);
}

export function createLogEntry(payload: LogEntryInput): Promise<LogEntryOut> {
  return apiFetch<LogEntryOut>("/api/v1/logs", { method: "POST", body: JSON.stringify(payload) });
}

export function deleteLogEntry(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/logs/${id}`, { method: "DELETE" });
}
