import enum

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RdaSex(str, enum.Enum):
    male = "male"
    female = "female"
    any = "any"


class RdaTarget(Base):
    """Static seed data (RDA tables) — powers the LLM daily/weekly gap
    analysis; the LLM never computes this itself, see nutrition_calc.py."""

    __tablename__ = "rda_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nutrient_code: Mapped[str] = mapped_column(
        String(16), ForeignKey("nutrient_reference.code"), nullable=False
    )
    sex: Mapped[RdaSex] = mapped_column(Enum(RdaSex, native_enum=False), nullable=False)
    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    rda_amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
