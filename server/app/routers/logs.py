from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.db.session import get_db
from app.models.food_nutrients import FoodNutrients
from app.models.log_entry import LogEntry
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_targets import UserTargets
from app.routers.foods import _to_food_out
from app.routers.targets import _get_active_targets
from app.schemas.log_entry import (
    DailySummary,
    LogEntryCreate,
    LogEntryOut,
    LogEntryUpdate,
    NutrientTotals,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


def _resolve_log_date(logged_at: datetime, tz_name: str) -> date:
    try:
        from zoneinfo import ZoneInfo

        local = logged_at.astimezone(ZoneInfo(tz_name))
    except Exception:
        local = logged_at
    return local.date()


def _user_timezone(db: Session, user_id: str) -> str:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    return profile.timezone if profile and profile.timezone else "UTC"


def _to_log_out(entry: LogEntry, db: Session) -> LogEntryOut:
    out = LogEntryOut.model_validate(entry)
    if entry.food_id:
        from app.models.food import Food

        food = db.get(Food, entry.food_id)
        if food:
            out.food = _to_food_out(food, db)
    return out


@router.get("", response_model=list[LogEntryOut])
def list_logs(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LogEntryOut]:
    entries = (
        db.query(LogEntry)
        .filter(
            LogEntry.user_id == current_user.id,
            LogEntry.log_date == date_,
            LogEntry.deleted_at.is_(None),
        )
        .order_by(LogEntry.logged_at.asc())
        .all()
    )
    return [_to_log_out(e, db) for e in entries]


def _sum_totals(entries: list[LogEntry], db: Session) -> NutrientTotals:
    totals = NutrientTotals()
    for entry in entries:
        if entry.food_id and entry.quantity_g is not None:
            nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == entry.food_id).first()
            if nutrients:
                factor = entry.quantity_g / 100.0
                totals.calories_kcal += nutrients.calories_kcal * factor
                totals.protein_g += nutrients.protein_g * factor
                totals.carbs_g += nutrients.carbs_g * factor
                totals.fat_g += nutrients.fat_g * factor
        elif entry.recipe_id and entry.quantity_servings is not None:
            from app.services.recipe_calc import recipe_nutrients_per_serving

            per_serving = recipe_nutrients_per_serving(db, entry.recipe_id)
            if per_serving:
                factor = entry.quantity_servings
                totals.calories_kcal += per_serving.calories_kcal * factor
                totals.protein_g += per_serving.protein_g * factor
                totals.carbs_g += per_serving.carbs_g * factor
                totals.fat_g += per_serving.fat_g * factor
    for field in ("calories_kcal", "protein_g", "carbs_g", "fat_g"):
        setattr(totals, field, round(getattr(totals, field), 1))
    return totals


@router.get("/summary", response_model=DailySummary)
def daily_summary(
    date_: date = Query(alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailySummary:
    entries = (
        db.query(LogEntry)
        .filter(
            LogEntry.user_id == current_user.id,
            LogEntry.log_date == date_,
            LogEntry.deleted_at.is_(None),
        )
        .order_by(LogEntry.logged_at.asc())
        .all()
    )
    totals = _sum_totals(entries, db)
    active_targets = _get_active_targets(db, current_user.id)
    targets = None
    if active_targets:
        targets = NutrientTotals(
            calories_kcal=active_targets.calories_kcal,
            protein_g=active_targets.protein_g,
            carbs_g=active_targets.carbs_g,
            fat_g=active_targets.fat_g,
        )
    return DailySummary(
        date=date_, totals=totals, targets=targets, entries=[_to_log_out(e, db) for e in entries]
    )


@router.get("/summary/weekly", response_model=list[DailySummary])
def weekly_summary(
    start: date,
    end: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DailySummary]:
    if end < start or (end - start) > timedelta(days=31):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")

    active_targets = _get_active_targets(db, current_user.id)
    targets = None
    if active_targets:
        targets = NutrientTotals(
            calories_kcal=active_targets.calories_kcal,
            protein_g=active_targets.protein_g,
            carbs_g=active_targets.carbs_g,
            fat_g=active_targets.fat_g,
        )

    summaries: list[DailySummary] = []
    current = start
    while current <= end:
        entries = (
            db.query(LogEntry)
            .filter(
                LogEntry.user_id == current_user.id,
                LogEntry.log_date == current,
                LogEntry.deleted_at.is_(None),
            )
            .order_by(LogEntry.logged_at.asc())
            .all()
        )
        summaries.append(
            DailySummary(
                date=current,
                totals=_sum_totals(entries, db),
                targets=targets,
                entries=[_to_log_out(e, db) for e in entries],
            )
        )
        current += timedelta(days=1)
    return summaries


@router.post("", response_model=LogEntryOut, status_code=status.HTTP_201_CREATED)
def create_log_entry(
    payload: LogEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogEntryOut:
    now = datetime.now(timezone.utc)
    tz_name = _user_timezone(db, current_user.id)
    entry = LogEntry(
        id=new_uuid(),
        user_id=current_user.id,
        food_id=payload.food_id,
        recipe_id=payload.recipe_id,
        quantity_g=payload.quantity_g,
        quantity_servings=payload.quantity_servings,
        meal_type=payload.meal_type,
        logged_at=payload.logged_at,
        log_date=_resolve_log_date(payload.logged_at, tz_name),
        notes=payload.notes,
        updated_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _to_log_out(entry, db)


@router.put("/{log_id}", response_model=LogEntryOut)
def update_log_entry(
    log_id: str,
    payload: LogEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogEntryOut:
    entry = db.get(LogEntry, log_id)
    if entry is None or entry.deleted_at is not None or entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    if "logged_at" in update_data:
        tz_name = _user_timezone(db, current_user.id)
        entry.log_date = _resolve_log_date(entry.logged_at, tz_name)

    entry.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return _to_log_out(entry, db)


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log_entry(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = db.get(LogEntry, log_id)
    if entry is None or entry.deleted_at is not None or entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")

    entry.deleted_at = datetime.now(timezone.utc)
    entry.updated_at = entry.deleted_at
    db.commit()
    return None
