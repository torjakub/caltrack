import base64
import json

import httpx

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError
from app.llm.prompts import OCR_SYSTEM_PROMPT, meal_analysis_prompt, period_analysis_prompt
from app.schemas.llm import MealInsight, MealNutritionData, NutrientGapReport, OCRNutritionResult, PeriodAnalysis, UserContext


class OllamaProvider(LLMProvider):
    """Points at a machine on the LAN running Ollama — not the Pi itself,
    which isn't powerful enough (see docs/llm-providers.md)."""

    provider_name = "ollama"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def _chat(self, *, model: str, prompt: str, images: list[str] | None = None) -> dict:
        if not model:
            raise LLMUnavailableError()
        message: dict = {"role": "user", "content": prompt}
        if images:
            message["images"] = images
        try:
            resp = httpx.post(
                f"{settings.ollama_host}/api/chat",
                json={"model": model, "messages": [message], "stream": False, "format": "json"},
                timeout=60.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"Ollama request failed (is it reachable on your LAN?): {e}") from e

        data = resp.json()
        try:
            return json.loads(data["message"]["content"])
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise LLMUnavailableError(f"Could not parse Ollama response: {e}") from e

    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        result = self._chat(model=settings.ollama_vision_model, prompt=OCR_SYSTEM_PROMPT, images=[b64])
        return OCRNutritionResult(**result)

    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        result = self._chat(model=settings.ollama_text_model, prompt=meal_analysis_prompt(nutrition_data, user_context))
        return MealInsight(**result)

    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        result = self._chat(
            model=settings.ollama_text_model, prompt=period_analysis_prompt(nutrient_gaps, user_context)
        )
        return PeriodAnalysis(**result)
