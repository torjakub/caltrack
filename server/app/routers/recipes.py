from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.db.session import get_db
from app.models.recipe import Recipe
from app.models.recipe_item import RecipeItem
from app.models.user import User
from app.schemas.recipe import RecipeCreate, RecipeOut, RecipeUpdate
from app.services.auth_service import get_current_user
from app.services.recipe_calc import recipe_nutrients_per_serving

router = APIRouter(prefix="/api/v1/recipes", tags=["recipes"])


def _to_recipe_out(recipe: Recipe, db: Session) -> RecipeOut:
    items = db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).all()
    out = RecipeOut.model_validate(recipe)
    out.items = items
    out.nutrients_per_serving = recipe_nutrients_per_serving(db, recipe.id)
    return out


def _get_owned_recipe(db: Session, recipe_id: str, user_id: str) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or recipe.deleted_at is not None or recipe.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    return recipe


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[RecipeOut]:
    recipes = (
        db.query(Recipe)
        .filter(Recipe.user_id == current_user.id, Recipe.deleted_at.is_(None))
        .order_by(Recipe.name.asc())
        .all()
    )
    return [_to_recipe_out(r, db) for r in recipes]


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    recipe = _get_owned_recipe(db, recipe_id, current_user.id)
    return _to_recipe_out(recipe, db)


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    now = datetime.now(timezone.utc)
    recipe = Recipe(
        id=new_uuid(),
        user_id=current_user.id,
        name=payload.name,
        servings=payload.servings,
        instructions=payload.instructions,
        updated_at=now,
    )
    db.add(recipe)
    db.flush()

    for item in payload.items:
        db.add(
            RecipeItem(
                id=new_uuid(),
                recipe_id=recipe.id,
                food_id=item.food_id,
                quantity_g=item.quantity_g,
            )
        )

    db.commit()
    db.refresh(recipe)
    return _to_recipe_out(recipe, db)


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: str,
    payload: RecipeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecipeOut:
    recipe = _get_owned_recipe(db, recipe_id, current_user.id)

    recipe.name = payload.name
    recipe.servings = payload.servings
    recipe.instructions = payload.instructions
    recipe.updated_at = datetime.now(timezone.utc)

    # Items sync as a whole with their parent recipe (see docs/sync-protocol.md)
    # — simplest correct approach here is replace-all rather than diffing.
    db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).delete()
    for item in payload.items:
        db.add(
            RecipeItem(
                id=new_uuid(),
                recipe_id=recipe.id,
                food_id=item.food_id,
                quantity_g=item.quantity_g,
            )
        )

    db.commit()
    db.refresh(recipe)
    return _to_recipe_out(recipe, db)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    recipe = _get_owned_recipe(db, recipe_id, current_user.id)
    recipe.deleted_at = datetime.now(timezone.utc)
    recipe.updated_at = recipe.deleted_at
    db.commit()
    return None
