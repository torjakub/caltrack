from datetime import date

from app.models.user_profile import ActivityLevel, Goal, Sex
from app.services.nutrition_calc import (
    calculate_age_years,
    calculate_bmr_mifflin_st_jeor,
    calculate_targets,
    compute_nutrient_gaps,
)


def test_calculate_age_years_before_birthday_this_year():
    # Born May 1; "today" is April 30 the same year they'd turn N -> still N-1
    assert calculate_age_years(date(1995, 5, 1), on_date=date(2026, 4, 30)) == 30


def test_calculate_age_years_on_or_after_birthday():
    assert calculate_age_years(date(1995, 5, 1), on_date=date(2026, 5, 1)) == 31
    assert calculate_age_years(date(1995, 5, 1), on_date=date(2026, 8, 21)) == 31


def test_bmr_mifflin_st_jeor_male_vs_female_offset():
    # Same body stats, only sex differs -> male should be exactly 166 kcal
    # higher (offset is +5 for male, -161 for female -> 166 kcal delta).
    male = calculate_bmr_mifflin_st_jeor(sex=Sex.male, weight_kg=80, height_cm=180, age_years=30)
    female = calculate_bmr_mifflin_st_jeor(sex=Sex.female, weight_kg=80, height_cm=180, age_years=30)
    assert male - female == 166


def test_calculate_targets_maintain_floor_and_macro_consistency():
    targets = calculate_targets(
        sex=Sex.male,
        weight_kg=80,
        height_cm=180,
        date_of_birth=date(1995, 5, 1),
        activity_level=ActivityLevel.moderate,
        goal=Goal.maintain,
    )
    assert targets.calories_kcal > 1200  # floor shouldn't bind for a normal maintain case
    # protein/fat/carb calories should sum to ~total calories (within rounding)
    macro_kcal = targets.protein_g * 4 + targets.fat_g * 9 + targets.carbs_g * 4
    assert abs(macro_kcal - targets.calories_kcal) < 5


def test_calculate_targets_never_goes_below_safety_floor():
    # An extreme cut rate on a small, sedentary body should still floor at 1200
    targets = calculate_targets(
        sex=Sex.female,
        weight_kg=45,
        height_cm=150,
        date_of_birth=date(1995, 5, 1),
        activity_level=ActivityLevel.sedentary,
        goal=Goal.lose,
        weekly_goal_rate_kg=-2.0,
    )
    assert targets.calories_kcal == 1200


def test_calculate_targets_lose_goal_has_lower_calories_than_maintain():
    common = dict(
        sex=Sex.male,
        weight_kg=90,
        height_cm=180,
        date_of_birth=date(1990, 1, 1),
        activity_level=ActivityLevel.active,
    )
    maintain = calculate_targets(goal=Goal.maintain, **common)
    lose = calculate_targets(goal=Goal.lose, weekly_goal_rate_kg=-0.5, **common)
    assert lose.calories_kcal < maintain.calories_kcal


def test_compute_nutrient_gaps_only_flags_shortfalls():
    gaps = compute_nutrient_gaps(
        consumed_totals={"CA": 200.0, "VITC": 120.0},
        rda_by_nutrient={
            "CA": (1000.0, "mg", "Calcium"),
            "VITC": (90.0, "mg", "Vitamin C"),
        },
    )
    codes = {g.nutrient_code for g in gaps}
    assert "CA" in codes  # 200/1000 -> big shortfall
    assert "VITC" not in codes  # 120 consumed > 90 RDA -> no gap


def test_compute_nutrient_gaps_severity_bands_and_sort_order():
    gaps = compute_nutrient_gaps(
        consumed_totals={"A": 0.0, "B": 85.0, "C": 60.0},
        rda_by_nutrient={
            "A": (100.0, "mg", "A"),  # 100% short -> severe
            "B": (100.0, "mg", "B"),  # 15% short -> mild
            "C": (100.0, "mg", "C"),  # 40% short -> moderate
        },
    )
    by_code = {g.nutrient_code: g for g in gaps}
    assert by_code["A"].severity == "severe"
    assert by_code["B"].severity == "mild"
    assert by_code["C"].severity == "moderate"
    # sorted by shortfall ratio descending: A (1.0) > C (0.4) > B (0.15)
    assert [g.nutrient_code for g in gaps] == ["A", "C", "B"]


def test_compute_nutrient_gaps_ignores_zero_or_negative_rda():
    gaps = compute_nutrient_gaps(consumed_totals={}, rda_by_nutrient={"X": (0.0, "mg", "X")})
    assert gaps == []
