from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.nutrient_reference import NutrientReference
from app.models.user import User
from app.schemas.nutrient import NutrientReferenceOut
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/nutrients", tags=["nutrients"])


@router.get("/reference", response_model=list[NutrientReferenceOut])
def list_nutrient_reference(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[NutrientReference]:
    return db.query(NutrientReference).order_by(NutrientReference.category, NutrientReference.display_name).all()
