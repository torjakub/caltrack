from datetime import date, datetime

from pydantic import BaseModel

from app.models.user_targets import TargetSource


class UserTargetsOut(BaseModel):
    id: str
    user_id: str
    effective_date: date
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None
    source: TargetSource
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserTargetsManualUpdate(BaseModel):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None = None
