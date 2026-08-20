from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class FoodNutrients(UUIDPKMixin, SyncableMixin, Base):
    """Core macros per 100g. Pulled out as first-class columns (rather than
    folded into the food_micronutrients EAV table) because every daily
    summary query needs exactly these four numbers."""

    __tablename__ = "food_nutrients"

    food_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("foods.id"), unique=True, nullable=False
    )
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
