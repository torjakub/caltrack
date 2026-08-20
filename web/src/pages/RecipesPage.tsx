import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { listRecipes, createRecipe, deleteRecipe } from "../api/recipes";
import { searchFoods } from "../api/foods";
import type { RecipeOut, FoodOut } from "../api/types";
import { ApiError } from "../api/client";

export function RecipesPage() {
  const [recipes, setRecipes] = useState<RecipeOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  async function load() {
    try {
      setRecipes(await listRecipes());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load recipes");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id: string) {
    await deleteRecipe(id);
    load();
  }

  return (
    <div className="page">
      <div className="dashboard-header">
        <h2>Recipes</h2>
        <button onClick={() => setShowForm((v) => !v)}>{showForm ? "Cancel" : "+ New recipe"}</button>
      </div>

      {error && <p className="error">{error}</p>}

      {showForm && (
        <RecipeForm
          onCreated={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      <ul className="entry-list">
        {recipes.map((recipe) => (
          <li key={recipe.id} style={{ flexDirection: "column", alignItems: "stretch" }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
              <strong>{recipe.name}</strong>
              <button className="link-button" onClick={() => handleDelete(recipe.id)}>
                Delete
              </button>
            </div>
            <span className="hint">
              {recipe.servings} servings
              {recipe.nutrients_per_serving &&
                ` · ${Math.round(recipe.nutrients_per_serving.calories_kcal)} kcal/serving`}
            </span>
          </li>
        ))}
        {recipes.length === 0 && !showForm && <p className="hint">No recipes yet.</p>}
      </ul>
    </div>
  );
}

interface DraftItem {
  food: FoodOut;
  quantity_g: number;
}

function RecipeForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [servings, setServings] = useState(1);
  const [instructions, setInstructions] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<FoodOut[]>([]);
  const [items, setItems] = useState<DraftItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      setResults(await searchFoods(query.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed");
    }
  }

  function addItem(food: FoodOut) {
    setItems((prev) => [...prev, { food, quantity_g: 100 }]);
    setResults([]);
    setQuery("");
  }

  function updateQuantity(index: number, quantity_g: number) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, quantity_g } : it)));
  }

  function removeItem(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (items.length === 0) {
      setError("Add at least one ingredient.");
      return;
    }
    try {
      await createRecipe({
        name,
        servings,
        instructions: instructions || null,
        items: items.map((it) => ({ food_id: it.food.id, quantity_g: it.quantity_g })),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create recipe");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="log-form" style={{ marginBottom: "1.5rem" }}>
      <label>
        Name
        <input value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label>
        Servings
        <input
          type="number"
          min={1}
          value={servings}
          onChange={(e) => setServings(Number(e.target.value))}
          required
        />
      </label>
      <label>
        Instructions (optional)
        <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={3} />
      </label>

      <div>
        <p className="hint">Ingredients</p>
        {items.map((it, i) => (
          <div key={i} className="inline-form">
            <span style={{ flex: 1 }}>{it.food.name}</span>
            <input
              type="number"
              min={1}
              value={it.quantity_g}
              onChange={(e) => updateQuantity(i, Number(e.target.value))}
              style={{ width: "80px" }}
            />
            <span className="hint">g</span>
            <button type="button" className="link-button" onClick={() => removeItem(i)}>
              Remove
            </button>
          </div>
        ))}
      </div>

      <div className="inline-form">
        <input
          placeholder="Search ingredients…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="button" onClick={handleSearch}>
          Search
        </button>
      </div>
      <ul className="food-results">
        {results.map((food) => (
          <li key={food.id}>
            <button type="button" className="food-result-button" onClick={() => addItem(food)}>
              {food.name}
              {food.brand && ` — ${food.brand}`}
            </button>
          </li>
        ))}
      </ul>

      {error && <p className="error">{error}</p>}
      <button type="submit">Create recipe</button>
    </form>
  );
}
