import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class TargetSource(str, enum.Enum):
    calculated = "calculated"
    manual = "manual"


class UserTargets(UUIDPKMixin, SyncableMixin, Base):
    """Versioned history — a new row per change, never overwritten in place.
    The active target is the most recent row with effective_date <= today."""

    __tablename__ = "user_targets"
    __table_args__ = (Index("ix_user_targets_user_effective", "user_id", "effective_date"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False)
    fat_g: Mapped[float] = mapped_column(Float, nullable=False)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[TargetSource] = mapped_column(
        Enum(TargetSource, native_enum=False), nullable=False
    )
