from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_targets import TargetSource, UserTargets
from app.schemas.targets import UserTargetsManualUpdate, UserTargetsOut
from app.services.auth_service import get_current_user
from app.services.nutrition_calc import calculate_targets

router = APIRouter(prefix="/api/v1/targets", tags=["targets"])


def _get_active_targets(db: Session, user_id: str) -> UserTargets | None:
    return (
        db.query(UserTargets)
        .filter(
            UserTargets.user_id == user_id,
            UserTargets.deleted_at.is_(None),
            UserTargets.effective_date <= date.today(),
        )
        .order_by(UserTargets.effective_date.desc(), UserTargets.updated_at.desc())
        .first()
    )


@router.get("", response_model=UserTargetsOut)
def get_targets(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserTargets:
    targets = _get_active_targets(db, current_user.id)
    if targets is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No targets set yet — call POST /targets/recalculate or set manually",
        )
    return targets


@router.put("", response_model=UserTargetsOut)
def set_targets_manually(
    payload: UserTargetsManualUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserTargets:
    now = datetime.now(timezone.utc)
    targets = UserTargets(
        id=new_uuid(),
        user_id=current_user.id,
        effective_date=date.today(),
        source=TargetSource.manual,
        updated_at=now,
        **payload.model_dump(),
    )
    db.add(targets)
    db.commit()
    db.refresh(targets)
    return targets


@router.post("/recalculate", response_model=UserTargetsOut)
def recalculate_targets(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserTargets:
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    missing = [
        field
        for field in ("sex", "weight_kg", "height_cm", "date_of_birth", "activity_level", "goal")
        if profile is None or getattr(profile, field) is None
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile incomplete, missing: {', '.join(missing)}",
        )

    result = calculate_targets(
        sex=profile.sex,
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        date_of_birth=profile.date_of_birth,
        activity_level=profile.activity_level,
        goal=profile.goal,
        weekly_goal_rate_kg=profile.weekly_goal_rate_kg,
    )

    now = datetime.now(timezone.utc)
    targets = UserTargets(
        id=new_uuid(),
        user_id=current_user.id,
        effective_date=date.today(),
        source=TargetSource.calculated,
        updated_at=now,
        **result._asdict(),
    )
    db.add(targets)
    db.commit()
    db.refresh(targets)
    return targets
