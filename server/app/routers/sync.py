from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.sync import SyncRequest, SyncResolveRequest, SyncResponse
from app.services import sync_engine
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post("", response_model=SyncResponse)
def sync(
    payload: SyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResponse:
    applied, conflicts = sync_engine.apply_push(
        db,
        changes=payload.changes.model_dump(),
        user_id=current_user.id,
        since=payload.since,
    )

    synced_at = datetime.now(timezone.utc)
    server_changes = sync_engine.collect_pull(db, user_id=current_user.id, since=payload.since)
    sync_engine.upsert_device(
        db,
        user_id=current_user.id,
        device_id=payload.device_id,
        device_name=payload.device_name,
        platform=payload.platform,
        synced_at=synced_at,
    )

    db.commit()

    return SyncResponse(
        synced_at=synced_at,
        applied=applied,
        conflicts=conflicts,
        server_changes=server_changes,
    )


@router.post("/resolve", response_model=SyncResponse)
def resolve(
    payload: SyncResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyncResponse:
    changes: dict[str, list[dict]] = {}
    for resolution in payload.resolutions:
        if resolution.resolution == "theirs" or resolution.record is None:
            continue
        # A resolution is itself a new write — force a fresh server-assigned
        # updated_at rather than reusing whatever the client last saw
        # (see docs/sync-protocol.md's resolution semantics).
        record = {**resolution.record, "updated_at": None}
        changes.setdefault(resolution.entity_type, []).append(record)

    # since=None forces every record through (bypasses conflict detection —
    # the user already made the call), matching docs/sync-protocol.md's
    # "applied as a new write" resolution semantics.
    applied, _ = sync_engine.apply_push(db, changes=changes, user_id=current_user.id, since=None)

    synced_at = datetime.now(timezone.utc)
    device = db.query(Device).filter(Device.user_id == current_user.id, Device.device_id == payload.device_id).first()
    server_changes = sync_engine.collect_pull(
        db, user_id=current_user.id, since=device.last_synced_at if device else None
    )

    db.commit()

    return SyncResponse(synced_at=synced_at, applied=applied, conflicts=[], server_changes=server_changes)


@router.get("/devices")
def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    devices = db.query(Device).filter(Device.user_id == current_user.id).all()
    return [
        {
            "device_id": d.device_id,
            "device_name": d.device_name,
            "platform": d.platform,
            "last_synced_at": d.last_synced_at,
            "last_seen_at": d.last_seen_at,
        }
        for d in devices
    ]
