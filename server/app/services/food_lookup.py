"""Food search/lookup: local DB first, then Open Food Facts (barcode) and
USDA FoodData Central (generic foods), caching any external fetch into the
local `foods`/`food_nutrients` tables so subsequent lookups are DB-only.
"""

import re
from datetime import datetime, timezone

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import new_uuid
from app.models.food import Food, FoodSource
from app.models.food_micronutrients import FoodMicronutrient
from app.models.food_nutrients import FoodNutrients

# Open Food Facts nutriment field (per 100g) -> (our nutrient_reference code,
# multiplier to convert OFF's value into that code's unit). OFF reports most
# *_100g fields in grams regardless of the nutrient's natural scale, so mg/mcg
# nutrients need scaling up. Best-effort — fine for a personal-use app, not a
# clinical source.
OFF_MICRONUTRIENT_FIELDS: dict[str, tuple[str, float]] = {
    "fiber_100g": ("FIBTG", 1),
    "sugars_100g": ("SUGAR", 1),
    "saturated-fat_100g": ("FASAT", 1),
    "sodium_100g": ("NA", 1000),
    "cholesterol_100g": ("CHOLE", 1000),
    "potassium_100g": ("K", 1000),
    "calcium_100g": ("CA", 1000),
    "iron_100g": ("FE", 1000),
    "vitamin-c_100g": ("VITC", 1000),
    "vitamin-d_100g": ("VITD", 1_000_000),
    "vitamin-a_100g": ("VITA", 1_000_000),
}

# USDA FDC nutrientName -> our nutrient_reference code. FDC values are
# already in each nutrient's standard unit (g/mg/mcg), matching
# nutrient_reference — no scaling needed.
USDA_MICRONUTRIENT_FIELDS: dict[str, str] = {
    "Fiber, total dietary": "FIBTG",
    "Sugars, total including NLEA": "SUGAR",
    "Sugars, total": "SUGAR",
    "Fatty acids, total saturated": "FASAT",
    "Sodium, Na": "NA",
    "Cholesterol": "CHOLE",
    "Potassium, K": "K",
    "Calcium, Ca": "CA",
    "Iron, Fe": "FE",
    "Vitamin C, total ascorbic acid": "VITC",
    "Vitamin D (D2 + D3)": "VITD",
    "Vitamin A, RAE": "VITA",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _extract_off_micronutrients(nutriments: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    for field, (code, multiplier) in OFF_MICRONUTRIENT_FIELDS.items():
        value = nutriments.get(field)
        if value is not None:
            result[code] = round(value * multiplier, 4)
    return result


def _extract_usda_micronutrients(nutrients_by_name: dict[str, float]) -> dict[str, float]:
    result: dict[str, float] = {}
    for name, code in USDA_MICRONUTRIENT_FIELDS.items():
        value = nutrients_by_name.get(name)
        if value is not None and code not in result:
            result[code] = round(value, 4)
    return result


def search_local(db: Session, query: str, limit: int = 25) -> list[Food]:
    like = f"%{query}%"
    return (
        db.query(Food)
        .filter(Food.deleted_at.is_(None))
        .filter(or_(Food.name.ilike(like), Food.brand.ilike(like)))
        .order_by(Food.is_custom.desc(), Food.name.asc())
        .limit(limit)
        .all()
    )


def get_by_barcode_local(db: Session, barcode: str) -> Food | None:
    return (
        db.query(Food)
        .filter(Food.barcode == barcode, Food.deleted_at.is_(None))
        .order_by(Food.is_custom.desc())
        .first()
    )


def _cache_food(
    db: Session,
    *,
    source: FoodSource,
    source_id: str | None,
    barcode: str | None,
    name: str,
    brand: str | None,
    serving_size_g: float | None,
    serving_unit_label: str | None,
    image_url: str | None,
    calories_kcal: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    micronutrients: dict[str, float] | None = None,
) -> Food:
    now = _now()
    food = Food(
        id=new_uuid(),
        source=source,
        source_id=source_id,
        barcode=barcode,
        name=name,
        brand=brand,
        serving_size_g=serving_size_g,
        serving_unit_label=serving_unit_label,
        image_url=image_url,
        is_custom=False,
        updated_at=now,
    )
    db.add(food)
    db.flush()

    db.add(
        FoodNutrients(
            id=new_uuid(),
            food_id=food.id,
            calories_kcal=calories_kcal,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            updated_at=now,
        )
    )

    for code, amount in (micronutrients or {}).items():
        db.add(
            FoodMicronutrient(
                id=new_uuid(),
                food_id=food.id,
                nutrient_code=code,
                amount_per_100g=amount,
                updated_at=now,
            )
        )

    db.commit()
    db.refresh(food)
    return food


def fetch_off_by_barcode(db: Session, barcode: str) -> Food | None:
    """Fetch a product from Open Food Facts by barcode and cache it locally.
    OFF's public read API needs no API key. Returns None if not found."""
    url = f"{settings.off_api_base_url}/api/v2/product/{barcode}.json"
    try:
        resp = httpx.get(url, timeout=10.0, headers={"User-Agent": "calTrack/0.1"})
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return None

    if data.get("status") != 1 or "product" not in data:
        return None

    product = data["product"]
    nutriments = product.get("nutriments", {})

    calories_kcal = nutriments.get("energy-kcal_100g")
    if calories_kcal is None:
        # Fall back to kJ if kcal isn't provided directly (1 kcal = 4.184 kJ)
        energy_kj = nutriments.get("energy_100g")
        calories_kcal = round(energy_kj / 4.184, 1) if energy_kj is not None else None

    if calories_kcal is None:
        return None  # not enough data to be useful

    return _cache_food(
        db,
        source=FoodSource.off,
        source_id=barcode,
        barcode=barcode,
        name=product.get("product_name") or product.get("generic_name") or "Unknown product",
        brand=product.get("brands"),
        serving_size_g=_parse_serving_grams(product.get("serving_size")),
        serving_unit_label=product.get("serving_size"),
        image_url=product.get("image_front_small_url") or product.get("image_url"),
        calories_kcal=calories_kcal,
        protein_g=nutriments.get("proteins_100g", 0.0) or 0.0,
        carbs_g=nutriments.get("carbohydrates_100g", 0.0) or 0.0,
        fat_g=nutriments.get("fat_100g", 0.0) or 0.0,
        micronutrients=_extract_off_micronutrients(nutriments),
    )


_SERVING_SIZE_GRAMS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*g\b", re.IGNORECASE)
_SERVING_SIZE_ANY_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def _parse_serving_grams(serving_size: str | None) -> float | None:
    """Extracts the gram amount from a serving-size label. OFF's
    serving_size field is free text like "30 g" or "1 slice (30g)" — prefer
    the number actually attached to a "g" unit (30) over an unrelated count
    earlier in the string (the "1" in "1 slice"), falling back to the first
    number found if no explicit gram unit is present."""
    if not serving_size:
        return None
    grams_match = _SERVING_SIZE_GRAMS_RE.search(serving_size)
    if grams_match:
        return float(grams_match.group(1))
    any_number_match = _SERVING_SIZE_ANY_NUMBER_RE.search(serving_size)
    return float(any_number_match.group()) if any_number_match else None


def search_usda(db: Session, query: str, limit: int = 10) -> list[Food]:
    """Search USDA FoodData Central for generic/whole foods and cache results
    locally. Requires USDA_FDC_API_KEY (free signup)."""
    if not settings.usda_fdc_api_key:
        return []

    url = f"{settings.usda_fdc_base_url}/foods/search"
    params = {
        "api_key": settings.usda_fdc_api_key,
        "query": query,
        "pageSize": limit,
        "dataType": ["Foundation", "SR Legacy"],
    }
    try:
        resp = httpx.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError:
        return []

    cached: list[Food] = []
    for item in data.get("foods", []):
        fdc_id = str(item.get("fdcId"))
        existing = (
            db.query(Food)
            .filter(Food.source == FoodSource.usda, Food.source_id == fdc_id)
            .first()
        )
        if existing:
            cached.append(existing)
            continue

        nutrients = {n.get("nutrientName"): n.get("value") for n in item.get("foodNutrients", [])}
        calories = nutrients.get("Energy")
        if calories is None:
            continue

        cached.append(
            _cache_food(
                db,
                source=FoodSource.usda,
                source_id=fdc_id,
                barcode=None,
                name=item.get("description", "Unknown food"),
                brand=item.get("brandOwner"),
                serving_size_g=None,
                serving_unit_label=None,
                image_url=None,
                calories_kcal=calories or 0.0,
                protein_g=nutrients.get("Protein", 0.0) or 0.0,
                carbs_g=nutrients.get("Carbohydrate, by difference", 0.0) or 0.0,
                fat_g=nutrients.get("Total lipid (fat)", 0.0) or 0.0,
                micronutrients=_extract_usda_micronutrients(nutrients),
            )
        )
    return cached


def search_foods(db: Session, query: str, limit: int = 25) -> list[Food]:
    """Local-first search with external fallback. Custom/local foods always
    rank first (see search_local's ordering)."""
    local_results = search_local(db, query, limit=limit)
    if len(local_results) >= limit:
        return local_results

    remaining = limit - len(local_results)
    usda_results = search_usda(db, query, limit=remaining)
    existing_ids = {f.id for f in local_results}
    for food in usda_results:
        if food.id not in existing_ids:
            local_results.append(food)
            existing_ids.add(food.id)

    return local_results[:limit]


def lookup_barcode(db: Session, barcode: str) -> Food | None:
    """Local cache first, then Open Food Facts (USDA has no barcode lookup)."""
    local = get_by_barcode_local(db, barcode)
    if local:
        return local
    return fetch_off_by_barcode(db, barcode)
