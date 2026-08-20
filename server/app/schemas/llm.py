from pydantic import BaseModel


class LLMStatus(BaseModel):
    provider: str
    available: bool


class OCRNutritionResult(BaseModel):
    name: str | None = None
    serving_size_g: float | None = None
    calories_kcal: float | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    micronutrients: dict[str, float] = {}


class MealInsight(BaseModel):
    summary: str
    positives: list[str] = []
    concerns: list[str] = []
    suggestions: list[str] = []


class NutrientDeficiency(BaseModel):
    nutrient: str
    gap_amount: float
    unit: str
    severity: str


class FoodSuggestion(BaseModel):
    food: str
    reason: str


class PeriodAnalysis(BaseModel):
    summary: str
    deficiencies: list[NutrientDeficiency] = []
    suggestions: list[FoodSuggestion] = []
