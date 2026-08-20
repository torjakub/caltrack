import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class MealType(str, enum.Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class LogEntry(UUIDPKMixin, SyncableMixin, Base):
    __tablename__ = "log_entries"
    __table_args__ = (
        CheckConstraint(
            "(food_id IS NOT NULL AND recipe_id IS NULL) OR "
            "(food_id IS NULL AND recipe_id IS NOT NULL)",
            name="ck_log_entries_exactly_one_of_food_recipe",
        ),
        Index("ix_log_entries_user_date", "user_id", "log_date"),
        Index("ix_log_entries_user_updated", "user_id", "updated_at"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    food_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("foods.id"), nullable=True)
    recipe_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recipes.id"), nullable=True
    )
    quantity_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_servings: Mapped[float | None] = mapped_column(Float, nullable=True)
    meal_type: Mapped[MealType] = mapped_column(Enum(MealType, native_enum=False), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
