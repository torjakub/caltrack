"""Unit tests for food_lookup.py's pure-logic parsing helpers. The actual
OFF/USDA HTTP calls are verified manually against the real APIs (see
docs/architecture.md) rather than mocked here — these tests cover the
string/unit-conversion logic that's easy to get subtly wrong.
"""

from app.services.food_lookup import (
    _extract_off_micronutrients,
    _extract_usda_micronutrients,
    _parse_serving_grams,
)


def test_parse_serving_grams_extracts_number():
    assert _parse_serving_grams("30g") == 30.0


def test_parse_serving_grams_prefers_number_attached_to_gram_unit():
    # OFF's serving_size is free text like "1 slice (30g)" — the gram
    # amount (30) should win over an unrelated leading count (the "1" in
    # "1 slice").
    assert _parse_serving_grams("1 slice (30g)") == 30.0


def test_parse_serving_grams_falls_back_to_first_number_without_gram_unit():
    assert _parse_serving_grams("2 pieces") == 2.0


def test_parse_serving_grams_handles_decimal():
    assert _parse_serving_grams("12.5g") == 12.5


def test_parse_serving_grams_none_input():
    assert _parse_serving_grams(None) is None
    assert _parse_serving_grams("") is None


def test_parse_serving_grams_no_digits():
    assert _parse_serving_grams("a serving") is None


def test_extract_off_micronutrients_converts_units():
    nutriments = {
        "fiber_100g": 2.5,
        "sugars_100g": 10.0,
        "sodium_100g": 0.4,  # OFF reports sodium in g -> should become 400mg
        "vitamin-c_100g": 0.05,  # g -> 50mg
    }
    result = _extract_off_micronutrients(nutriments)
    assert result["FIBTG"] == 2.5
    assert result["SUGAR"] == 10.0
    assert result["NA"] == 400.0
    assert result["VITC"] == 50.0


def test_extract_off_micronutrients_skips_missing_fields():
    result = _extract_off_micronutrients({"fiber_100g": 3.0})
    assert result == {"FIBTG": 3.0}


def test_extract_usda_micronutrients_maps_known_names():
    nutrients = {
        "Fiber, total dietary": 4.0,
        "Sodium, Na": 250.0,
        "Vitamin C, total ascorbic acid": 12.0,
        "Some Unrelated Nutrient": 999.0,
    }
    result = _extract_usda_micronutrients(nutrients)
    assert result == {"FIBTG": 4.0, "NA": 250.0, "VITC": 12.0}


def test_extract_usda_micronutrients_first_matching_name_wins():
    # Both "Sugars, total including NLEA" and "Sugars, total" map to SUGAR —
    # whichever appears first in USDA_MICRONUTRIENT_FIELDS iteration order
    # should win, and the second must not overwrite it.
    nutrients = {"Sugars, total including NLEA": 5.0, "Sugars, total": 999.0}
    result = _extract_usda_micronutrients(nutrients)
    assert result["SUGAR"] == 5.0
