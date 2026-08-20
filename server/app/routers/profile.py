from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.profile import UserProfileOut, UserProfileUpdate
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def _get_or_create_profile(db: Session, user_id: str) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(id=new_uuid(), user_id=user_id, updated_at=datetime.now(timezone.utc))
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=UserProfileOut)
def get_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserProfile:
    return _get_or_create_profile(db, current_user.id)


@router.put("", response_model=UserProfileOut)
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    profile = _get_or_create_profile(db, current_user.id)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return profile
