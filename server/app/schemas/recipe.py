from datetime import datetime

from pydantic import BaseModel


class RecipeItemIn(BaseModel):
    food_id: str
    quantity_g: float


class RecipeItemOut(RecipeItemIn):
    id: str

    model_config = {"from_attributes": True}


class RecipeCreate(BaseModel):
    name: str
    servings: float = 1.0
    instructions: str | None = None
    items: list[RecipeItemIn] = []


class RecipeUpdate(RecipeCreate):
    pass


class RecipeNutrientsPerServing(BaseModel):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class RecipeOut(BaseModel):
    id: str
    user_id: str
    name: str
    servings: float
    instructions: str | None
    updated_at: datetime
    items: list[RecipeItemOut] = []
    nutrients_per_serving: RecipeNutrientsPerServing | None = None

    model_config = {"from_attributes": True}
