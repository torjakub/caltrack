from datetime import date, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.base import LLMUnavailableError
from app.llm.factory import get_llm_provider
from app.models.food import Food
from app.models.food_micronutrients import FoodMicronutrient
from app.models.food_nutrients import FoodNutrients
from app.models.log_entry import LogEntry
from app.models.nutrient_reference import NutrientReference
from app.models.rda_targets import RdaTarget
from app.models.recipe import Recipe
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_targets import UserTargets
from app.schemas.llm import (
    LLMStatus,
    MealInsight,
    MealItem,
    MealNutritionData,
    NutrientGapItem,
    NutrientGapReport,
    NutrientTotalsLLM,
    OCRNutritionResult,
    PeriodAnalysis,
    UserContext,
)
from app.services.auth_service import get_current_user
from app.services.nutrition_calc import calculate_age_years, compute_nutrient_gaps
from app.services.recipe_calc import recipe_nutrients_per_serving

# 10 MB is far above any real nutrition-label photo; the cap exists purely to
# stop a runaway upload from exhausting memory on a small device.
MAX_IMAGE_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


def _build_user_context(db: Session, user_id: str) -> UserContext:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    active_targets = (
        db.query(UserTargets)
        .filter(
            UserTargets.user_id == user_id,
            UserTargets.deleted_at.is_(None),
            UserTargets.effective_date <= date.today(),
        )
        .order_by(UserTargets.effective_date.desc(), UserTargets.updated_at.desc())
        .first()
    )
    return UserContext(
        display_name=profile.display_name if profile else None,
        sex=profile.sex.value if profile and profile.sex else None,
        age_years=calculate_age_years(profile.date_of_birth) if profile and profile.date_of_birth else None,
        activity_level=profile.activity_level.value if profile and profile.activity_level else None,
        goal=profile.goal.value if profile and profile.goal else None,
        weight_kg=profile.weight_kg if profile else None,
        height_cm=profile.height_cm if profile else None,
        calorie_target=active_targets.calories_kcal if active_targets else None,
        protein_target_g=active_targets.protein_g if active_targets else None,
        carbs_target_g=active_targets.carbs_g if active_targets else None,
        fat_target_g=active_targets.fat_g if active_targets else None,
    )


def _build_meal_nutrition_data(db: Session, entry: LogEntry) -> MealNutritionData:
    items: list[MealItem] = []
    totals = NutrientTotalsLLM(calories_kcal=0, protein_g=0, carbs_g=0, fat_g=0)

    if entry.food_id and entry.quantity_g is not None:
        food = db.get(Food, entry.food_id)
        nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == entry.food_id).first()
        if food and nutrients:
            factor = entry.quantity_g / 100.0
            item = MealItem(
                name=food.name,
                quantity_g=entry.quantity_g,
                calories_kcal=round(nutrients.calories_kcal * factor, 1),
                protein_g=round(nutrients.protein_g * factor, 1),
                carbs_g=round(nutrients.carbs_g * factor, 1),
                fat_g=round(nutrients.fat_g * factor, 1),
            )
            items.append(item)
            totals = NutrientTotalsLLM(
                calories_kcal=item.calories_kcal,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
            )
    elif entry.recipe_id and entry.quantity_servings is not None:
        recipe = db.get(Recipe, entry.recipe_id)
        per_serving = recipe_nutrients_per_serving(db, entry.recipe_id)
        if recipe and per_serving:
            factor = entry.quantity_servings
            item = MealItem(
                name=recipe.name,
                quantity_servings=entry.quantity_servings,
                calories_kcal=round(per_serving.calories_kcal * factor, 1),
                protein_g=round(per_serving.protein_g * factor, 1),
                carbs_g=round(per_serving.carbs_g * factor, 1),
                fat_g=round(per_serving.fat_g * factor, 1),
            )
            items.append(item)
            totals = NutrientTotalsLLM(
                calories_kcal=item.calories_kcal,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
            )

    return MealNutritionData(
        meal_type=entry.meal_type.value, logged_at=entry.logged_at.isoformat(), items=items, totals=totals
    )


def _build_nutrient_gap_report(db: Session, user: User, start: date, end: date) -> NutrientGapReport:
    entries = (
        db.query(LogEntry)
        .filter(
            LogEntry.user_id == user.id,
            LogEntry.log_date >= start,
            LogEntry.log_date <= end,
            LogEntry.deleted_at.is_(None),
        )
        .all()
    )

    totals = {"calories_kcal": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
    micro_totals: dict[str, float] = {}
    for entry in entries:
        if entry.food_id and entry.quantity_g is not None:
            factor = entry.quantity_g / 100.0
            nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == entry.food_id).first()
            if nutrients:
                totals["calories_kcal"] += nutrients.calories_kcal * factor
                totals["protein_g"] += nutrients.protein_g * factor
                totals["carbs_g"] += nutrients.carbs_g * factor
                totals["fat_g"] += nutrients.fat_g * factor
            micros = db.query(FoodMicronutrient).filter(FoodMicronutrient.food_id == entry.food_id).all()
            for m in micros:
                micro_totals[m.nutrient_code] = micro_totals.get(m.nutrient_code, 0.0) + m.amount_per_100g * factor

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    sex = profile.sex.value if profile and profile.sex else None
    rda_rows = db.query(RdaTarget).filter(RdaTarget.sex.in_([sex, "any"] if sex else ["any"])).all()
    nutrient_names = {n.code: n.display_name for n in db.query(NutrientReference).all()}
    rda_by_nutrient = {r.nutrient_code: (r.rda_amount, r.unit, nutrient_names.get(r.nutrient_code, r.nutrient_code)) for r in rda_rows}

    num_days = (end - start).days + 1
    avg_micro_totals = {k: v / num_days for k, v in micro_totals.items()}
    gaps = compute_nutrient_gaps(consumed_totals=avg_micro_totals, rda_by_nutrient=rda_by_nutrient)

    active_targets = (
        db.query(UserTargets)
        .filter(UserTargets.user_id == user.id, UserTargets.deleted_at.is_(None), UserTargets.effective_date <= date.today())
        .order_by(UserTargets.effective_date.desc())
        .first()
    )
    targets = (
        NutrientTotalsLLM(
            calories_kcal=active_targets.calories_kcal,
            protein_g=active_targets.protein_g,
            carbs_g=active_targets.carbs_g,
            fat_g=active_targets.fat_g,
        )
        if active_targets
        else None
    )

    return NutrientGapReport(
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        totals=NutrientTotalsLLM(**{k: round(v / num_days, 1) for k, v in totals.items()}),
        targets=targets,
        gaps=[
            NutrientGapItem(
                nutrient_code=g.nutrient_code,
                display_name=g.display_name,
                consumed=g.consumed,
                rda_amount=g.rda_amount,
                gap_amount=g.gap_amount,
                unit=g.unit,
                severity=g.severity,
            )
            for g in gaps
        ],
    )


@router.get("/status", response_model=LLMStatus)
def llm_status(_current_user: User = Depends(get_current_user)) -> LLMStatus:
    provider = get_llm_provider()
    return LLMStatus(provider=provider.provider_name, available=provider.is_available())


@router.post("/ocr-nutrition-label", response_model=OCRNutritionResult)
def ocr_nutrition_label(
    image: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
) -> OCRNutritionResult:
    provider = get_llm_provider()
    # Read in bounded chunks so an oversized upload is rejected before it can
    # exhaust memory on the Pi.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = image.file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large (max 10 MB)")
        chunks.append(chunk)
    image_bytes = b"".join(chunks)
    try:
        return provider.ocr_nutrition_label(image_bytes, image.content_type or "image/jpeg")
    except LLMUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "llm_unavailable", "message": str(e)}) from e


@router.post("/meal-review/{log_entry_id}", response_model=MealInsight)
def meal_review(
    log_entry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealInsight:
    entry = db.get(LogEntry, log_entry_id)
    if entry is None or entry.deleted_at is not None or entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")

    provider = get_llm_provider()
    try:
        nutrition_data = _build_meal_nutrition_data(db, entry)
        user_context = _build_user_context(db, current_user.id)
        return provider.analyze_meal(nutrition_data, user_context)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "llm_unavailable", "message": str(e)}) from e


@router.post("/analysis/daily", response_model=PeriodAnalysis)
def analysis_daily(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PeriodAnalysis:
    provider = get_llm_provider()
    try:
        report = _build_nutrient_gap_report(db, current_user, date_, date_)
        user_context = _build_user_context(db, current_user.id)
        return provider.analyze_period(report, user_context)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "llm_unavailable", "message": str(e)}) from e


@router.post("/analysis/weekly", response_model=PeriodAnalysis)
def analysis_weekly(
    start: date,
    end: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PeriodAnalysis:
    if end < start or (end - start) > timedelta(days=31):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    provider = get_llm_provider()
    try:
        report = _build_nutrient_gap_report(db, current_user, start, end)
        user_context = _build_user_context(db, current_user.id)
        return provider.analyze_period(report, user_context)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"error": "llm_unavailable", "message": str(e)}) from e
