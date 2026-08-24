from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator


def _check_records(value: Any) -> Any:
    """Turn malformed records into clean 422s instead of KeyErrors/ValueErrors
    deep inside sync_engine."""
    if not isinstance(value, list):
        return value
    for record in value:
        if not isinstance(record, dict):
            raise ValueError("each sync record must be an object")
        if not isinstance(record.get("id"), str) or not record["id"]:
            raise ValueError("each sync record needs a non-empty string 'id'")
        if "updated_at" not in record:
            raise ValueError(f"record {record.get('id')} needs an 'updated_at' field")
    return value


def _check_record(record: Any) -> Any:
    """Same checks as _check_records but for a single optional record."""
    if record is None:
        return None
    if not isinstance(record, dict):
        raise ValueError("sync record must be an object")
    if not isinstance(record.get("id"), str) or not record["id"]:
        raise ValueError("sync record needs a non-empty string 'id'")
    if "updated_at" not in record:
        raise ValueError(f"record {record.get('id')} needs an 'updated_at' field")
    return record


RecordList = Annotated[list[dict[str, Any]], BeforeValidator(_check_records)]
OptionalRecord = Annotated[dict[str, Any] | None, BeforeValidator(_check_record)]


class SyncChanges(BaseModel):
    user_profile: RecordList = []
    user_targets: RecordList = []
    foods: RecordList = []
    food_nutrients: RecordList = []
    food_micronutrients: RecordList = []
    recipes: RecordList = []
    log_entries: RecordList = []


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
    entity_type: Literal[
        "user_profile",
        "user_targets",
        "foods",
        "food_nutrients",
        "food_micronutrients",
        "recipes",
        "log_entries",
    ]
    id: str
    resolution: Literal["mine", "theirs", "manual"]
    record: OptionalRecord = None


class SyncResolveRequest(BaseModel):
    device_id: str
    resolutions: list[SyncResolution]
