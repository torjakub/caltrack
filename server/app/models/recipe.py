from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncableMixin, UUIDPKMixin


class Recipe(UUIDPKMixin, SyncableMixin, Base):
    __tablename__ = "recipes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    servings: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
