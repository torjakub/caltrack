import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDailySummary, deleteLogEntry } from "../api/logs";
import { getProfile } from "../api/profile";
import { getNutrientReference } from "../api/nutrients";
import type { DailySummary, MealType, NutrientReferenceOut } from "../api/types";
import { ApiError } from "../api/client";

// The server buckets log entries into a calendar day using the user's
// profile timezone (see server/app/routers/logs.py:_resolve_log_date), not
// the browser's local clock — so "today" here must be computed the same way
// or a fresh entry can silently land outside the default view.
function todayInTimezone(timezone: string): string {
  try {
    return new Intl.DateTimeFormat("en-CA", { timeZone: timezone }).format(new Date());
  } catch {
    return new Date().toISOString().slice(0, 10);
  }
}

const MEAL_LABELS: Record<MealType, string> = {
  breakfast: "Breakfast",
  lunch: "Lunch",
  dinner: "Dinner",
  snack: "Snack",
};

export function DashboardPage() {
  const [date, setDate] = useState<string | null>(null);
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [nutrientReference, setNutrientReference] = useState<NutrientReferenceOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProfile()
      .then((profile) => setDate(todayInTimezone(profile.timezone)))
      .catch(() => setDate(todayInTimezone("UTC")));
    getNutrientReference()
      .then(setNutrientReference)
      .catch(() => setNutrientReference([]));
  }, []);

  async function load() {
    if (!date) return;
    setLoading(true);
    setError(null);
    try {
      setSummary(await getDailySummary(date));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load summary");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date]);

  async function handleDelete(id: string) {
    await deleteLogEntry(id);
    load();
  }

  const entriesByMeal: Record<MealType, typeof summary extends null ? never : DailySummary["entries"]> =
    { breakfast: [], lunch: [], dinner: [], snack: [] };
  summary?.entries.forEach((e) => entriesByMeal[e.meal_type].push(e));

  return (
    <div className="page">
      <div className="dashboard-header">
        <input type="date" value={date ?? ""} onChange={(e) => setDate(e.target.value)} />
        <Link to="/log" className="button-link">
          + Log food
        </Link>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p className="error">{error}</p>}

      {summary && (
        <>
          <div className="totals-card">
            <TotalRow
              label="Calories"
              value={summary.totals.calories_kcal}
              target={summary.targets?.calories_kcal}
              unit="kcal"
            />
            <TotalRow
              label="Protein"
              value={summary.totals.protein_g}
              target={summary.targets?.protein_g}
              unit="g"
            />
            <TotalRow
              label="Carbs"
              value={summary.totals.carbs_g}
              target={summary.targets?.carbs_g}
              unit="g"
            />
            <TotalRow label="Fat" value={summary.totals.fat_g} target={summary.targets?.fat_g} unit="g" />
            {!summary.targets && (
              <p className="hint">
                No targets set yet — go to <Link to="/profile">Profile</Link> to calculate them.
              </p>
            )}
          </div>

          {(Object.keys(MEAL_LABELS) as MealType[]).map((meal) => (
            <div key={meal} className="meal-section">
              <h3>{MEAL_LABELS[meal]}</h3>
              {entriesByMeal[meal].length === 0 && <p className="hint">Nothing logged</p>}
              <ul className="entry-list">
                {entriesByMeal[meal].map((entry) => (
                  <li key={entry.id}>
                    <span>
                      {entry.food?.name ?? entry.recipe_name ?? "Unknown"}
                      {entry.quantity_g != null && ` — ${entry.quantity_g}g`}
                      {entry.quantity_servings != null && ` — ${entry.quantity_servings} servings`}
                    </span>
                    <button className="link-button" onClick={() => handleDelete(entry.id)}>
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          {Object.keys(summary.micronutrient_totals).length > 0 && (
            <div className="targets-card">
              <h3>Micronutrients</h3>
              <ul>
                {Object.entries(summary.micronutrient_totals).map(([code, amount]) => {
                  const ref = nutrientReference.find((n) => n.code === code);
                  return (
                    <li key={code}>
                      {ref?.display_name ?? code}: {amount} {ref?.unit ?? ""}
                    </li>
                  );
                })}
              </ul>
              <p className="hint">Recipe-based entries aren't included yet.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function TotalRow({
  label,
  value,
  target,
  unit,
}: {
  label: string;
  value: number;
  target?: number;
  unit: string;
}) {
  return (
    <div className="total-row">
      <span className="total-label">{label}</span>
      <span className="total-value">
        {Math.round(value)} {unit}
        {target != null && <span className="total-target"> / {Math.round(target)} {unit}</span>}
      </span>
    </div>
  );
}
