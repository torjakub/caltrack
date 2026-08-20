from datetime import date, datetime

from pydantic import BaseModel

from app.models.user_profile import ActivityLevel, Goal, Sex


class UserProfileBase(BaseModel):
    display_name: str | None = None
    date_of_birth: date | None = None
    sex: Sex | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    activity_level: ActivityLevel | None = None
    goal: Goal | None = None
    weekly_goal_rate_kg: float | None = None
    timezone: str = "UTC"


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileOut(UserProfileBase):
    id: str
    user_id: str
    updated_at: datetime

    model_config = {"from_attributes": True}
