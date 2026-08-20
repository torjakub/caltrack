import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class SyncableMixin:
    """Adds the updated_at/deleted_at pair every syncable table needs
    for the sync protocol's conflict detection (see docs/sync-protocol.md)."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
