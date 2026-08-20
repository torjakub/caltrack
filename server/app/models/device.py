import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPKMixin


class DevicePlatform(str, enum.Enum):
    ios = "ios"
    android = "android"
    web = "web"


class Device(UUIDPKMixin, Base):
    """Server-only sync checkpoint per device. Not synced itself."""

    __tablename__ = "devices"
    __table_args__ = (Index("ux_devices_user_device", "user_id", "device_id", unique=True),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    platform: Mapped[DevicePlatform] = mapped_column(
        Enum(DevicePlatform, native_enum=False), nullable=False
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
