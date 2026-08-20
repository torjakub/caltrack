import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { searchFoods, lookupBarcode, createCustomFood } from "../api/foods";
import { createLogEntry } from "../api/logs";
import { listRecipes } from "../api/recipes";
import type { FoodOut, MealType, RecipeOut } from "../api/types";
import { ApiError } from "../api/client";

export function LogMealPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [barcode, setBarcode] = useState("");
  const [results, setResults] = useState<FoodOut[]>([]);
  const [selected, setSelected] = useState<FoodOut | null>(null);
  const [quantityG, setQuantityG] = useState(100);
  const [recipes, setRecipes] = useState<RecipeOut[]>([]);
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeOut | null>(null);
  const [quantityServings, setQuantityServings] = useState(1);
  const [mealType, setMealType] = useState<MealType>("breakfast");
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const [showCustomForm, setShowCustomForm] = useState(false);

  useEffect(() => {
    listRecipes()
      .then(setRecipes)
      .catch(() => setRecipes([]));
  }, []);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      setResults(await searchFoods(query.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function handleBarcodeSubmit(e: FormEvent) {
    e.preventDefault();
    if (!barcode.trim()) return;
    setError(null);
    setSearching(true);
    try {
      const food = await lookupBarcode(barcode.trim());
      setSelected(food);
      setResults([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Barcode not found");
    } finally {
      setSearching(false);
    }
  }

  async function handleLog(e: FormEvent) {
    e.preventDefault();
    if (!selected && !selectedRecipe) return;
    setError(null);
    try {
      await createLogEntry(
        selectedRecipe
          ? {
              recipe_id: selectedRecipe.id,
              quantity_servings: quantityServings,
              meal_type: mealType,
              logged_at: new Date().toISOString(),
            }
          : {
              food_id: selected!.id,
              quantity_g: quantityG,
              meal_type: mealType,
              logged_at: new Date().toISOString(),
            }
      );
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to log entry");
    }
  }

  return (
    <div className="page">
      <h2>Log food</h2>

      {!selected && !selectedRecipe && (
        <>
          {recipes.length > 0 && (
            <>
              <p className="hint">Recipes</p>
              <ul className="food-results">
                {recipes.map((recipe) => (
                  <li key={recipe.id}>
                    <button className="food-result-button" onClick={() => setSelectedRecipe(recipe)}>
                      <strong>{recipe.name}</strong>
                      {recipe.nutrients_per_serving && (
                        <span className="hint">
                          {" "}
                          · {Math.round(recipe.nutrients_per_serving.calories_kcal)} kcal/serving
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          <form onSubmit={handleSearch} className="inline-form">
            <input
              placeholder="Search foods…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button type="submit" disabled={searching}>
              Search
            </button>
          </form>

          <form onSubmit={handleBarcodeSubmit} className="inline-form">
            <input
              placeholder="Enter barcode…"
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
            />
            <button type="submit" disabled={searching}>
              Look up
            </button>
          </form>

          {error && <p className="error">{error}</p>}

          <ul className="food-results">
            {results.map((food) => (
              <li key={food.id}>
                <button className="food-result-button" onClick={() => setSelected(food)}>
                  <strong>{food.name}</strong>
                  {food.brand && <span> — {food.brand}</span>}
                  {food.nutrients && (
                    <span className="hint"> · {Math.round(food.nutrients.calories_kcal)} kcal/100g</span>
                  )}
                </button>
              </li>
            ))}
          </ul>

          <button className="link-button" onClick={() => setShowCustomForm((v) => !v)}>
            {showCustomForm ? "Cancel" : "Can't find it? Add a custom food"}
          </button>

          {showCustomForm && (
            <CustomFoodForm
              onCreated={(food) => {
                setSelected(food);
                setShowCustomForm(false);
              }}
            />
          )}
        </>
      )}

      {(selected || selectedRecipe) && (
        <form onSubmit={handleLog} className="log-form">
          <h3>{selected ? selected.name : selectedRecipe!.name}</h3>
          {selected?.nutrients && (
            <p className="hint">
              {Math.round(selected.nutrients.calories_kcal)} kcal, {selected.nutrients.protein_g}g
              protein, {selected.nutrients.carbs_g}g carbs, {selected.nutrients.fat_g}g fat — per 100g
            </p>
          )}
          {selectedRecipe?.nutrients_per_serving && (
            <p className="hint">
              {Math.round(selectedRecipe.nutrients_per_serving.calories_kcal)} kcal,{" "}
              {selectedRecipe.nutrients_per_serving.protein_g}g protein,{" "}
              {selectedRecipe.nutrients_per_serving.carbs_g}g carbs,{" "}
              {selectedRecipe.nutrients_per_serving.fat_g}g fat — per serving
            </p>
          )}
          {selected && (
            <label>
              Quantity (g)
              <input
                type="number"
                min={1}
                value={quantityG}
                onChange={(e) => setQuantityG(Number(e.target.value))}
                required
              />
            </label>
          )}
          {selectedRecipe && (
            <label>
              Servings
              <input
                type="number"
                min={0.25}
                step={0.25}
                value={quantityServings}
                onChange={(e) => setQuantityServings(Number(e.target.value))}
                required
              />
            </label>
          )}
          <label>
            Meal
            <select value={mealType} onChange={(e) => setMealType(e.target.value as MealType)}>
              <option value="breakfast">Breakfast</option>
              <option value="lunch">Lunch</option>
              <option value="dinner">Dinner</option>
              <option value="snack">Snack</option>
            </select>
          </label>
          {error && <p className="error">{error}</p>}
          <div className="form-actions">
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setSelectedRecipe(null);
              }}
            >
              Back
            </button>
            <button type="submit">Log it</button>
          </div>
        </form>
      )}
    </div>
  );
}

function CustomFoodForm({ onCreated }: { onCreated: (food: FoodOut) => void }) {
  const [name, setName] = useState("");
  const [calories, setCalories] = useState(0);
  const [protein, setProtein] = useState(0);
  const [carbs, setCarbs] = useState(0);
  const [fat, setFat] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const food = await createCustomFood({
        name,
        calories_kcal: calories,
        protein_g: protein,
        carbs_g: carbs,
        fat_g: fat,
      });
      onCreated(food);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create food");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="custom-food-form">
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <p className="hint">Nutrition values are per 100g</p>
      <div className="macro-grid">
        <label>
          Calories (kcal)
          <input type="number" value={calories} onChange={(e) => setCalories(Number(e.target.value))} />
        </label>
        <label>
          Protein (g)
          <input type="number" value={protein} onChange={(e) => setProtein(Number(e.target.value))} />
        </label>
        <label>
          Carbs (g)
          <input type="number" value={carbs} onChange={(e) => setCarbs(Number(e.target.value))} />
        </label>
        <label>
          Fat (g)
          <input type="number" value={fat} onChange={(e) => setFat(Number(e.target.value))} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit">Create food</button>
    </form>
  );
}
