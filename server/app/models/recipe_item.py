from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class RecipeItem(UUIDPKMixin, Base):
    """Syncs as a nested payload under its parent recipe (applied
    transactionally), not conflict-checked independently — no
    updated_at/deleted_at of its own. See docs/sync-protocol.md."""

    __tablename__ = "recipe_items"

    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id"), nullable=False)
    food_id: Mapped[str] = mapped_column(String(36), ForeignKey("foods.id"), nullable=False)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)
