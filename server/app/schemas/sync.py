from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class SyncChanges(BaseModel):
    user_profile: list[dict[str, Any]] = []
    user_targets: list[dict[str, Any]] = []
    foods: list[dict[str, Any]] = []
    food_nutrients: list[dict[str, Any]] = []
    food_micronutrients: list[dict[str, Any]] = []
    recipes: list[dict[str, Any]] = []
    log_entries: list[dict[str, Any]] = []


class SyncRequest(BaseModel):
    device_id: str
    device_name: str | None = None
    platform: Literal["ios", "android", "web"]
    since: datetime | None = None
    changes: SyncChanges = SyncChanges()


class SyncConflict(BaseModel):
    entity_type: str
    id: str
    mine: dict[str, Any]
    theirs: dict[str, Any]


class SyncResponse(BaseModel):
    synced_at: datetime
    applied: dict[str, list[str]]
    conflicts: list[SyncConflict]
    server_changes: dict[str, list[dict[str, Any]]]


class SyncResolution(BaseModel):
    entity_type: str
    id: str
    resolution: Literal["mine", "theirs", "manual"]
    record: dict[str, Any] | None = None


class SyncResolveRequest(BaseModel):
    device_id: str
    resolutions: list[SyncResolution]
