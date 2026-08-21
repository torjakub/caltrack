from app.llm.base import LLMProvider, LLMUnavailableError
from app.schemas.llm import MealInsight, MealNutritionData, NutrientGapReport, OCRNutritionResult, PeriodAnalysis, UserContext


class NoneProvider(LLMProvider):
    provider_name = "none"

    def is_available(self) -> bool:
        return False

    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        raise LLMUnavailableError()

    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        raise LLMUnavailableError()

    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        raise LLMUnavailableError()
