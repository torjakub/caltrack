"""The LLM adapter interface every provider implements. Kept synchronous
(matching food_lookup.py's httpx usage elsewhere in this codebase) so
router handlers stay plain `def` functions.

All three feature methods either return their structured result or raise
LLMUnavailableError — routers catch that uniformly and return a 503 with a
consistent error shape, which both /web and /mobile check for to render
"LLM not configured" rather than a broken feature.
"""

from abc import ABC, abstractmethod

from app.schemas.llm import (
    MealInsight,
    MealNutritionData,
    NutrientGapReport,
    OCRNutritionResult,
    PeriodAnalysis,
    UserContext,
)


class LLMUnavailableError(Exception):
    def __init__(self, message: str = "LLM not configured") -> None:
        super().__init__(message)


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    def is_available(self) -> bool:
        """Cheap check: API key present, or a short-timeout reachability
        ping for a self-hosted backend like Ollama. Must never raise."""
        ...

    @abstractmethod
    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        """A photographed nutrition table -> structured macros/micros to
        prefill a new food entry. Raises LLMUnavailableError on any failure
        (not configured, network error, model declined, unparseable
        response) — callers don't need to distinguish why."""
        ...

    @abstractmethod
    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        """Feedback on a single logged meal."""
        ...

    @abstractmethod
    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        """Narrates a *pre-computed* nutrient gap report (see
        services/nutrition_calc.py) — the model never does the arithmetic,
        only explains numbers it's handed."""
        ...
