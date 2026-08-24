from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.db.session import get_db
from app.models.food import Food, FoodSource
from app.models.food_micronutrients import FoodMicronutrient
from app.models.food_nutrients import FoodNutrients
from app.models.user import User
from app.schemas.food import CustomFoodCreate, CustomFoodUpdate, FoodOut
from app.services import food_lookup
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/foods", tags=["foods"])


def _to_food_out(food: Food, db: Session) -> FoodOut:
    nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == food.id).first()
    micronutrients = (
        db.query(FoodMicronutrient).filter(FoodMicronutrient.food_id == food.id).all()
    )
    out = FoodOut.model_validate(food)
    if nutrients:
        out.nutrients = nutrients
    out.micronutrients = micronutrients
    return out


@router.get("/search", response_model=list[FoodOut])
def search_foods(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[FoodOut]:
    foods = food_lookup.search_foods(db, q)
    return [_to_food_out(f, db) for f in foods]


@router.get("/barcode/{barcode}", response_model=FoodOut)
def barcode_lookup(
    barcode: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FoodOut:
    food = food_lookup.lookup_barcode(db, barcode)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _to_food_out(food, db)


@router.get("/{food_id}", response_model=FoodOut)
def get_food(
    food_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FoodOut:
    food = db.get(Food, food_id)
    if food is None or food.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
    return _to_food_out(food, db)


@router.post("", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
def create_custom_food(
    payload: CustomFoodCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodOut:
    now = datetime.now(timezone.utc)
    food = Food(
        id=new_uuid(),
        source=FoodSource.local,
        name=payload.name,
        brand=payload.brand,
        serving_size_g=payload.serving_size_g,
        serving_unit_label=payload.serving_unit_label,
        is_custom=True,
        created_by_user_id=current_user.id,
        updated_at=now,
    )
    db.add(food)
    db.flush()
    db.add(
        FoodNutrients(
            id=new_uuid(),
            food_id=food.id,
            calories_kcal=payload.calories_kcal,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            updated_at=now,
        )
    )
    db.commit()
    db.refresh(food)
    return _to_food_out(food, db)


@router.put("/{food_id}", response_model=FoodOut)
def update_custom_food(
    food_id: str,
    payload: CustomFoodUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FoodOut:
    food = db.get(Food, food_id)
    if food is None or food.deleted_at is not None or not food.is_custom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom food not found")
    if food.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your food")

    now = datetime.now(timezone.utc)
    food.name = payload.name
    food.brand = payload.brand
    food.serving_size_g = payload.serving_size_g
    food.serving_unit_label = payload.serving_unit_label
    food.updated_at = now

    nutrients = db.query(FoodNutrients).filter(FoodNutrients.food_id == food.id).first()
    if nutrients is None:
        # A food without a nutrients row is malformed data, but an update
        # shouldn't 500 on it — create the missing row instead.
        nutrients = FoodNutrients(id=new_uuid(), food_id=food.id)
        db.add(nutrients)
    nutrients.calories_kcal = payload.calories_kcal
    nutrients.protein_g = payload.protein_g
    nutrients.carbs_g = payload.carbs_g
    nutrients.fat_g = payload.fat_g
    nutrients.updated_at = now

    db.commit()
    db.refresh(food)
    return _to_food_out(food, db)


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_food(
    food_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    food = db.get(Food, food_id)
    if food is None or food.deleted_at is not None or not food.is_custom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom food not found")
    if food.created_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your food")

    food.deleted_at = datetime.now(timezone.utc)
    food.updated_at = food.deleted_at
    db.commit()
    return None
