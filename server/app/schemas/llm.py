from pydantic import BaseModel


class LLMStatus(BaseModel):
    provider: str
    available: bool


class UserContext(BaseModel):
    """Everything an LLM feature might want to know about the user, computed
    in plain Python — never left for the model to derive or guess."""

    display_name: str | None = None
    sex: str | None = None
    age_years: int | None = None
    activity_level: str | None = None
    goal: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    calorie_target: float | None = None
    protein_target_g: float | None = None
    carbs_target_g: float | None = None
    fat_target_g: float | None = None


class MealItem(BaseModel):
    name: str
    quantity_g: float | None = None
    quantity_servings: float | None = None
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class NutrientTotalsLLM(BaseModel):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealNutritionData(BaseModel):
    meal_type: str
    logged_at: str
    items: list[MealItem]
    totals: NutrientTotalsLLM


class NutrientGapItem(BaseModel):
    nutrient_code: str
    display_name: str
    consumed: float
    rda_amount: float
    gap_amount: float
    unit: str
    severity: str


class NutrientGapReport(BaseModel):
    period_start: str
    period_end: str
    totals: NutrientTotalsLLM
    targets: NutrientTotalsLLM | None
    gaps: list[NutrientGapItem]


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
