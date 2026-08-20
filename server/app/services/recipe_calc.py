"""Recipe nutrition is always computed on the fly from recipe_items ×
food_nutrients, never cached, so it can't go stale when ingredients change."""

from sqlalchemy.orm import Session

from app.models.food_nutrients import FoodNutrients
from app.models.recipe import Recipe
from app.models.recipe_item import RecipeItem
from app.schemas.recipe import RecipeNutrientsPerServing


def recipe_nutrients_per_serving(db: Session, recipe_id: str) -> RecipeNutrientsPerServing | None:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.deleted_at is not None or not recipe.servings:
        return None

    items = db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe_id).all()
    if not items:
        return RecipeNutrientsPerServing(calories_kcal=0, protein_g=0, carbs_g=0, fat_g=0)

    totals = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    for item in items:
        nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == item.food_id).first()
        if not nutrients:
            continue
        factor = item.quantity_g / 100.0
        totals["calories_kcal"] += nutrients.calories_kcal * factor
        totals["protein_g"] += nutrients.protein_g * factor
        totals["carbs_g"] += nutrients.carbs_g * factor
        totals["fat_g"] += nutrients.fat_g * factor

    return RecipeNutrientsPerServing(
        calories_kcal=round(totals["calories_kcal"] / recipe.servings, 1),
        protein_g=round(totals["protein_g"] / recipe.servings, 1),
        carbs_g=round(totals["carbs_g"] / recipe.servings, 1),
        fat_g=round(totals["fat_g"] / recipe.servings, 1),
    )
