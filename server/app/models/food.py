import enum

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class FoodSource(str, enum.Enum):
    local = "local"
    off = "off"
    usda = "usda"


class Food(UUIDPKMixin, SyncableMixin, Base):
    __tablename__ = "foods"
    __table_args__ = (
        Index(
            "ux_foods_source_source_id",
            "source",
            "source_id",
            unique=True,
            sqlite_where=text("source_id IS NOT NULL"),
        ),
        Index("ix_foods_barcode", "barcode"),
        Index("ix_foods_name", "name"),
    )

    source: Mapped[FoodSource] = mapped_column(Enum(FoodSource, native_enum=False), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serving_size_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    serving_unit_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
