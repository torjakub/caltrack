"""Prompt text shared across providers — only the request plumbing differs
per API, the actual instructions should stay identical so behavior doesn't
quietly vary by provider."""

import json

from app.schemas.llm import MealNutritionData, NutrientGapReport, UserContext

OCR_SYSTEM_PROMPT = (
    "You are extracting nutrition facts from a photograph of a food product's nutrition label. "
    "Return ONLY a JSON object with these fields (per 100g if a per-100g column exists, otherwise "
    "per serving as labeled): name (product name if visible, else null), serving_size_g (number or "
    "null), calories_kcal, protein_g, carbs_g, fat_g, micronutrients (an object mapping any additional "
    "visible nutrients to their numeric amount, using these exact keys where applicable: FIBTG "
    "(fiber, g), SUGAR (sugars, g), FASAT (saturated fat, g), NA (sodium, mg), CHOLE (cholesterol, "
    "mg), K (potassium, mg), CA (calcium, mg), FE (iron, mg), VITC (vitamin C, mg), VITD (vitamin D, "
    "mcg), VITA (vitamin A, mcg)). Use null for any field you cannot read. Do not include any text "
    "outside the JSON object."
)


def user_context_line(user_context: UserContext) -> str:
    return json.dumps(user_context.model_dump(exclude_none=True))


def meal_analysis_prompt(nutrition_data: MealNutritionData, user_context: UserContext) -> str:
    return (
        "You are a nutrition assistant reviewing a single logged meal for a home nutrition-tracking "
        "app. All totals below are already computed — do not do any arithmetic yourself. Return ONLY "
        "a JSON object with fields: summary (1-2 sentence overview), positives (array of short "
        "strings), concerns (array of short strings, empty if none), suggestions (array of short "
        "actionable strings, empty if none). Be encouraging and specific, not generic.\n\n"
        f"User: {user_context_line(user_context)}\n"
        f"Meal ({nutrition_data.meal_type} at {nutrition_data.logged_at}):\n"
        f"Items: {json.dumps([i.model_dump() for i in nutrition_data.items])}\n"
        f"Totals: {json.dumps(nutrition_data.totals.model_dump())}"
    )


def period_analysis_prompt(nutrient_gaps: NutrientGapReport, user_context: UserContext) -> str:
    return (
        "You are a nutrition assistant summarizing a period of logged meals for a home "
        "nutrition-tracking app. All nutrient gaps below are ALREADY COMPUTED against RDA tables — "
        "do not recompute or second-guess the numbers, only narrate them. Return ONLY a JSON object "
        "with fields: summary (2-3 sentence overview of how the period went), deficiencies (array of "
        "{nutrient, gap_amount, unit, severity} — copy directly from the gaps given, do not invent "
        "new ones), suggestions (array of {food, reason} — realistic whole-food suggestions "
        "addressing the biggest gaps, 3-5 items).\n\n"
        f"User: {user_context_line(user_context)}\n"
        f"Period: {nutrient_gaps.period_start} to {nutrient_gaps.period_end}\n"
        f"Totals consumed: {json.dumps(nutrient_gaps.totals.model_dump())}\n"
        f"Targets: {json.dumps(nutrient_gaps.targets.model_dump()) if nutrient_gaps.targets else 'none set'}\n"
        f"Nutrient gaps (already computed): {json.dumps([g.model_dump() for g in nutrient_gaps.gaps])}"
    )
