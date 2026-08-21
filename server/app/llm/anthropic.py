import base64

import httpx

from app.core.config import settings
from app.llm.base import LLMProvider, LLMUnavailableError
from app.llm.prompts import OCR_SYSTEM_PROMPT, meal_analysis_prompt, period_analysis_prompt
from app.llm.utils import extract_json
from app.schemas.llm import MealInsight, MealNutritionData, NutrientGapReport, OCRNutritionResult, PeriodAnalysis, UserContext

JSON_ONLY_SUFFIX = "\n\nRespond with ONLY the JSON object — no other text, no markdown code fences."


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _messages(self, content: str | list[dict]) -> dict:
        if not settings.anthropic_api_key:
            raise LLMUnavailableError()
        try:
            resp = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers=self._headers(),
                json={
                    "model": settings.anthropic_model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": content}],
                },
                timeout=30.0,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMUnavailableError(f"Anthropic request failed: {e}") from e

        data = resp.json()
        try:
            text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
            return extract_json(text)
        except (KeyError, ValueError) as e:
            raise LLMUnavailableError(f"Could not parse Anthropic response: {e}") from e

    def ocr_nutrition_label(self, image_bytes: bytes, mime_type: str) -> OCRNutritionResult:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        content = [
            {"type": "text", "text": OCR_SYSTEM_PROMPT + JSON_ONLY_SUFFIX},
            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
        ]
        result = self._messages(content)
        return OCRNutritionResult(**result)

    def analyze_meal(self, nutrition_data: MealNutritionData, user_context: UserContext) -> MealInsight:
        result = self._messages(meal_analysis_prompt(nutrition_data, user_context) + JSON_ONLY_SUFFIX)
        return MealInsight(**result)

    def analyze_period(self, nutrient_gaps: NutrientGapReport, user_context: UserContext) -> PeriodAnalysis:
        result = self._messages(period_analysis_prompt(nutrient_gaps, user_context) + JSON_ONLY_SUFFIX)
        return PeriodAnalysis(**result)
