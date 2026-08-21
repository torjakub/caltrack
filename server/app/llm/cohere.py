import base64
import json

import httpx

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError
from app.llm.prompts import OCR_SYSTEM_PROMPT, meal_analysis_prompt, period_analysis_prompt
from app.schemas.llm import MealInsight, MealNutritionData, NutrientGapReport, OCRNutritionResult, PeriodAnalysis, UserContext


class CohereProvider(LLMProvider):
    provider_name = "cohere"

    def is_available(self) -> bool:
        return bool(settings.cohere_api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.cohere_api_key}", "Content-Type": "application/json"}

    def _chat(self, *, model: str, content: str | list[dict]) -> dict:
        if not settings.cohere_api_key:
            raise LLMUnavailableError()
        try:
            resp = httpx.post(
                f"{settings.cohere_api_base_url}/v2/chat",
                headers=self._headers(),
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"Cohere request failed: {e}") from e

        data = resp.json()
        try:
            text = "".join(
                block.get("text", "") for block in data["message"]["content"] if block.get("type") == "text"
            )
            return json.loads(text)
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise LLMUnavailableError(f"Could not parse Cohere response: {e}") from e

    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        content = [
            {"type": "text", "text": OCR_SYSTEM_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
        ]
        result = self._chat(model=settings.cohere_vision_model, content=content)
        return OCRNutritionResult(**result)

    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        result = self._chat(model=settings.cohere_text_model, content=meal_analysis_prompt(nutrition_data, user_context))
        return MealInsight(**result)

    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        result = self._chat(
            model=settings.cohere_text_model, content=period_analysis_prompt(nutrient_gaps, user_context)
        )
        return PeriodAnalysis(**result)
