import base64
import json

import httpx

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError
from app.llm.prompts import OCR_SYSTEM_PROMPT, meal_analysis_prompt, period_analysis_prompt
from app.schemas.llm import MealInsight, MealNutritionData, NutrientGapReport, OCRNutritionResult, PeriodAnalysis, UserContext


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def is_available(self) -> bool:
        return bool(settings.openai_api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}

    def _chat(self, content: str | list[dict]) -> dict:
        if not settings.openai_api_key:
            raise LLMUnavailableError()
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=self._headers(),
                json={
                    "model": settings.openai_model,
                    "messages": [{"role": "user", "content": content}],
                    "response_format": {"type": "json_object"},
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"OpenAI request failed: {e}") from e

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
            return json.loads(text)
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as e:
            raise LLMUnavailableError(f"Could not parse OpenAI response: {e}") from e

    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        content = [
            {"type": "text", "text": OCR_SYSTEM_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
        ]
        result = self._chat(content)
        return OCRNutritionResult(**result)

    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        result = self._chat(meal_analysis_prompt(nutrition_data, user_context))
        return MealInsight(**result)

    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        result = self._chat(period_analysis_prompt(nutrient_gaps, user_context))
        return PeriodAnalysis(**result)
