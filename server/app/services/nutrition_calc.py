"""Pure-Python nutrition math: calorie/macro targets and RDA gap analysis.

Kept deliberately free of any LLM calls — the LLM only ever narrates numbers
computed here (see app/llm/base.py: analyze_period()), never derives them.
"""

from datetime import date
from typing import NamedTuple

from app.models.user_profile import ActivityLevel, Goal, Sex

ACTIVITY_MULTIPLIERS = {
    ActivityLevel.sedentary: 1.2,
    ActivityLevel.light: 1.375,
    ActivityLevel.moderate: 1.55,
    ActivityLevel.active: 1.725,
    ActivityLevel.very_active: 1.9,
}

# kcal/day adjustment applied per kg/week of target weight change (~7700 kcal/kg)
KCAL_PER_KG = 7700


class MacroTargets(NamedTuple):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


def calculate_bmr_mifflin_st_jeor(
    *, sex: Sex, weight_kg: float, height_cm: float, age_years: int
) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age_years
    return base + (5 if sex == Sex.male else -161)


def calculate_age_years(date_of_birth: date, on_date: date | None = None) -> int:
    on_date = on_date or date.today()
    years = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def calculate_targets(
    *,
    sex: Sex,
    weight_kg: float,
    height_cm: float,
    date_of_birth: date,
    activity_level: ActivityLevel,
    goal: Goal,
    weekly_goal_rate_kg: float | None = None,
) -> MacroTargets:
    age_years = calculate_age_years(date_of_birth)
    bmr = calculate_bmr_mifflin_st_jeor(
        sex=sex, weight_kg=weight_kg, height_cm=height_cm, age_years=age_years
    )
    tdee = bmr * ACTIVITY_MULTIPLIERS[activity_level]

    daily_adjustment = 0.0
    if goal != Goal.maintain and weekly_goal_rate_kg:
        daily_adjustment = (weekly_goal_rate_kg * KCAL_PER_KG) / 7

    calories = max(tdee + daily_adjustment, 1200)  # floor to avoid unsafe targets

    protein_g = weight_kg * 1.8
    fat_g = (calories * 0.25) / 9
    remaining_kcal = calories - (protein_g * 4) - (fat_g * 9)
    carbs_g = max(remaining_kcal / 4, 0)
    fiber_g = 14 * (calories / 1000)

    return MacroTargets(
        calories_kcal=round(calories, 1),
        protein_g=round(protein_g, 1),
        carbs_g=round(carbs_g, 1),
        fat_g=round(fat_g, 1),
        fiber_g=round(fiber_g, 1),
    )


class NutrientGap(NamedTuple):
    nutrient_code: str
    display_name: str
    consumed: float
    rda_amount: float
    gap_amount: float
    unit: str
    severity: str


def compute_nutrient_gaps(
    *,
    consumed_totals: dict[str, float],
    rda_by_nutrient: dict[str, tuple[float, str, str]],
) -> list[NutrientGap]:
    """rda_by_nutrient maps nutrient_code -> (rda_amount, unit, display_name).
    Returns only nutrients where intake fell short of the RDA."""
    gaps: list[NutrientGap] = []
    for code, (rda_amount, unit, display_name) in rda_by_nutrient.items():
        consumed = consumed_totals.get(code, 0.0)
        if rda_amount <= 0:
            continue
        shortfall_ratio = (rda_amount - consumed) / rda_amount
        if shortfall_ratio <= 0:
            continue
        severity = "severe" if shortfall_ratio >= 0.5 else "moderate" if shortfall_ratio >= 0.2 else "mild"
        gaps.append(
            NutrientGap(
                nutrient_code=code,
                display_name=display_name,
                consumed=round(consumed, 1),
                rda_amount=rda_amount,
                gap_amount=round(rda_amount - consumed, 1),
                unit=unit,
                severity=severity,
            )
        )
    gaps.sort(key=lambda g: g.gap_amount / g.rda_amount, reverse=True)
    return gaps
