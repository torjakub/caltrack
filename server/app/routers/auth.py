from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import new_uuid
from app.db.session import get_db
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import LoginRequest, RefreshRequest, SetupRequest, TokenPair, UserOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/setup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def setup(payload: SetupRequest, db: Session = Depends(get_db)) -> TokenPair:
    if db.query(User).count() > 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Setup already complete")

    user = User(
        id=new_uuid(),
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()

    now = datetime.now(timezone.utc)
    db.add(
        UserProfile(
            id=new_uuid(),
            user_id=user.id,
            timezone=payload.timezone or "UTC",
            updated_at=now,
        )
    )
    db.commit()

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.get(User, data["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    # Stateless JWTs: nothing to invalidate server-side for v1. Client just
    # discards its tokens. A revocation list is a possible future addition
    # if that becomes necessary.
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
