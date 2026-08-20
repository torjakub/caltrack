from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class FoodMicronutrient(UUIDPKMixin, SyncableMixin, Base):
    """EAV table for everything besides the 4 core macros. USDA FDC exposes
    100+ nutrients; keeping this EAV avoids a wide, mostly-null foods table
    and schema churn every time one more nutrient is needed."""

    __tablename__ = "food_micronutrients"
    __table_args__ = (Index("ix_food_micronutrients_food_nutrient", "food_id", "nutrient_code"),)

    food_id: Mapped[str] = mapped_column(String(36), ForeignKey("foods.id"), nullable=False)
    nutrient_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("nutrient_reference.code"), nullable=False
    )
    amount_per_100g: Mapped[float] = mapped_column(Float, nullable=False)
