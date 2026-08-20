from datetime import datetime

from pydantic import BaseModel

from app.models.food import FoodSource


class FoodNutrientsOut(BaseModel):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float

    model_config = {"from_attributes": True}


class FoodMicronutrientOut(BaseModel):
    nutrient_code: str
    amount_per_100g: float

    model_config = {"from_attributes": True}


class FoodOut(BaseModel):
    id: str
    source: FoodSource
    barcode: str | None
    name: str
    brand: str | None
    serving_size_g: float | None
    serving_unit_label: str | None
    image_url: str | None
    is_custom: bool
    updated_at: datetime
    nutrients: FoodNutrientsOut | None = None
    micronutrients: list[FoodMicronutrientOut] = []

    model_config = {"from_attributes": True}


class CustomFoodCreate(BaseModel):
    name: str
    brand: str | None = None
    serving_size_g: float | None = None
    serving_unit_label: str | None = None
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class CustomFoodUpdate(CustomFoodCreate):
    pass
