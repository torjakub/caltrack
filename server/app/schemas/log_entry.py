from datetime import date, datetime

from pydantic import BaseModel, model_validator

from app.models.log_entry import MealType
from app.schemas.food import FoodOut


class LogEntryCreate(BaseModel):
    food_id: str | None = None
    recipe_id: str | None = None
    quantity_g: float | None = None
    quantity_servings: float | None = None
    meal_type: MealType
    logged_at: datetime
    notes: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> "LogEntryCreate":
        if (self.food_id is None) == (self.recipe_id is None):
            raise ValueError("Exactly one of food_id or recipe_id must be set")
        if self.food_id is not None and self.quantity_g is None:
            raise ValueError("quantity_g is required when logging a food")
        if self.recipe_id is not None and self.quantity_servings is None:
            raise ValueError("quantity_servings is required when logging a recipe")
        return self


class LogEntryUpdate(BaseModel):
    quantity_g: float | None = None
    quantity_servings: float | None = None
    meal_type: MealType | None = None
    logged_at: datetime | None = None
    notes: str | None = None


class LogEntryOut(BaseModel):
    id: str
    food_id: str | None
    recipe_id: str | None
    quantity_g: float | None
    quantity_servings: float | None
    meal_type: MealType
    logged_at: datetime
    log_date: date
    notes: str | None
    updated_at: datetime
    food: FoodOut | None = None
    recipe_name: str | None = None

    model_config = {"from_attributes": True}


class NutrientTotals(BaseModel):
    calories_kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0


class DailySummary(BaseModel):
    date: date
    totals: NutrientTotals
    targets: NutrientTotals | None
    micronutrient_totals: dict[str, float] = {}
    entries: list[LogEntryOut]
