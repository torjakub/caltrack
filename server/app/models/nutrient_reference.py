import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NutrientCategory(str, enum.Enum):
    macro = "macro"
    vitamin = "vitamin"
    mineral = "mineral"
    other = "other"


class NutrientReference(Base):
    """Static seed data — ships via a migration/seed script, not user-synced."""

    __tablename__ = "nutrient_reference"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[NutrientCategory] = mapped_column(
        Enum(NutrientCategory, native_enum=False), nullable=False
    )
