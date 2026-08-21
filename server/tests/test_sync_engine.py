"""Tests for the sync protocol's core conflict-detection algorithm — see
docs/sync-protocol.md. This is the highest-risk novel logic in the codebase,
so it gets the most direct coverage.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.models.log_entry import LogEntry
from app.models.recipe import Recipe
from app.models.recipe_item import RecipeItem
from app.models.user import User
from app.services import sync_engine


def iso(dt: datetime) -> str:
    return dt.isoformat()


def make_log_entry_record(
    *, record_id: str, food_id: str, quantity_g: float, updated_at: datetime, deleted_at: datetime | None = None
) -> dict:
    return {
        "id": record_id,
        "food_id": food_id,
        "recipe_id": None,
        "quantity_g": quantity_g,
        "quantity_servings": None,
        "meal_type": "breakfast",
        "logged_at": iso(updated_at),
        "log_date": updated_at.date().isoformat(),
        "notes": None,
        "updated_at": iso(updated_at),
        "deleted_at": iso(deleted_at) if deleted_at else None,
    }


def test_apply_push_inserts_new_record(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    changes = {
        "log_entries": [make_log_entry_record(record_id=record_id, food_id=new_uuid(), quantity_g=100, updated_at=t0)]
    }

    applied, conflicts = sync_engine.apply_push(db, changes=changes, user_id=user.id, since=None)
    db.commit()

    assert conflicts == []
    assert applied["log_entries"] == [record_id]
    row = db.get(LogEntry, record_id)
    assert row is not None
    assert row.quantity_g == 100
    assert row.user_id == user.id  # force-set, not trusted from client


def test_apply_push_updates_when_since_covers_existing_change(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    food_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    # Device's since is AFTER the existing row's updated_at -> clean update, no conflict.
    since = t0 + timedelta(seconds=1)
    t1 = t0 + timedelta(seconds=2)
    applied, conflicts = sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=150, updated_at=t1)]},
        user_id=user.id,
        since=since,
    )

    assert conflicts == []
    assert applied["log_entries"] == [record_id]
    assert db.get(LogEntry, record_id).quantity_g == 150


def test_apply_push_detects_conflict_when_since_predates_existing_change(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    food_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    # Simulate another device advancing the row past this device's since.
    t_other_device = t0 + timedelta(seconds=5)
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=150, updated_at=t_other_device)]},
        user_id=user.id,
        since=t0 + timedelta(seconds=1),  # after the FIRST write, before the second
    )
    db.commit()

    # This device's own since is stale relative to the second write -> conflict.
    stale_since = t0 + timedelta(seconds=1)
    t_this_device = t0 + timedelta(seconds=10)
    applied, conflicts = sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=200, updated_at=t_this_device)]},
        user_id=user.id,
        since=stale_since,
    )

    assert applied == {}
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["entity_type"] == "log_entries"
    assert conflict["id"] == record_id
    assert conflict["mine"]["quantity_g"] == 200
    assert conflict["theirs"]["quantity_g"] == 150
    # Server's current state must be untouched by the losing push.
    assert db.get(LogEntry, record_id).quantity_g == 150


def test_apply_push_first_sync_never_conflicts_even_with_existing_id(db: Session, user: User):
    # since=None (first-ever sync) always applies — a brand-new device has
    # no baseline to conflict against.
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    food_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    applied, conflicts = sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=999, updated_at=t0 + timedelta(seconds=1))]},
        user_id=user.id,
        since=None,
    )

    assert conflicts == []
    assert applied["log_entries"] == [record_id]


def test_apply_push_soft_delete_is_applied_like_any_other_write(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    food_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    t1 = t0 + timedelta(seconds=1)
    applied, conflicts = sync_engine.apply_push(
        db,
        changes={
            "log_entries": [
                make_log_entry_record(record_id=record_id, food_id=food_id, quantity_g=100, updated_at=t1, deleted_at=t1)
            ]
        },
        user_id=user.id,
        since=t0,
    )

    assert conflicts == []
    assert applied["log_entries"] == [record_id]
    assert db.get(LogEntry, record_id).deleted_at is not None


def test_collect_pull_only_returns_changes_after_since(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    old_id, new_id = new_uuid(), new_uuid()
    food_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=old_id, food_id=food_id, quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    checkpoint = t0 + timedelta(seconds=1)
    t1 = t0 + timedelta(seconds=2)
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=new_id, food_id=food_id, quantity_g=50, updated_at=t1)]},
        user_id=user.id,
        since=checkpoint,
    )
    db.commit()

    pulled = sync_engine.collect_pull(db, user_id=user.id, since=checkpoint)
    pulled_ids = {e["id"] for e in pulled["log_entries"]}
    assert pulled_ids == {new_id}


def test_collect_pull_since_none_returns_everything(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    record_id = new_uuid()
    sync_engine.apply_push(
        db,
        changes={"log_entries": [make_log_entry_record(record_id=record_id, food_id=new_uuid(), quantity_g=100, updated_at=t0)]},
        user_id=user.id,
        since=None,
    )
    db.commit()

    pulled = sync_engine.collect_pull(db, user_id=user.id, since=None)
    assert {e["id"] for e in pulled["log_entries"]} == {record_id}


def test_apply_recipes_replaces_items_wholesale(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    recipe_id = new_uuid()
    food_a, food_b = new_uuid(), new_uuid()
    record = {
        "id": recipe_id,
        "name": "Toast",
        "servings": 2,
        "instructions": None,
        "updated_at": iso(t0),
        "deleted_at": None,
        "items": [{"id": new_uuid(), "food_id": food_a, "quantity_g": 50}],
    }
    applied, conflicts = sync_engine.apply_push(db, changes={"recipes": [record]}, user_id=user.id, since=None)
    db.commit()
    assert conflicts == []
    assert applied["recipes"] == [recipe_id]
    assert db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe_id).count() == 1

    t1 = t0 + timedelta(seconds=1)
    updated_record = {**record, "updated_at": iso(t1), "items": [{"id": new_uuid(), "food_id": food_b, "quantity_g": 80}]}
    sync_engine.apply_push(db, changes={"recipes": [updated_record]}, user_id=user.id, since=t0)
    db.commit()

    items = db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe_id).all()
    assert len(items) == 1
    assert items[0].food_id == food_b


def test_apply_recipes_conflict_includes_current_items(db: Session, user: User):
    t0 = datetime.now(timezone.utc)
    recipe_id = new_uuid()
    food_id = new_uuid()
    record = {
        "id": recipe_id,
        "name": "Toast",
        "servings": 1,
        "instructions": None,
        "updated_at": iso(t0),
        "deleted_at": None,
        "items": [{"id": new_uuid(), "food_id": food_id, "quantity_g": 50}],
    }
    sync_engine.apply_push(db, changes={"recipes": [record]}, user_id=user.id, since=None)
    db.commit()

    # Someone else edits it after this device's stale checkpoint.
    t_other = t0 + timedelta(seconds=5)
    sync_engine.apply_push(
        db,
        changes={"recipes": [{**record, "updated_at": iso(t_other), "name": "Toast v2"}]},
        user_id=user.id,
        since=t0,
    )
    db.commit()

    t_mine = t0 + timedelta(seconds=10)
    applied, conflicts = sync_engine.apply_push(
        db,
        changes={"recipes": [{**record, "updated_at": iso(t_mine), "name": "My Toast"}]},
        user_id=user.id,
        since=t0,  # stale relative to t_other's write
    )

    assert applied == {}
    assert len(conflicts) == 1
    assert conflicts[0]["theirs"]["name"] == "Toast v2"
    assert "items" in conflicts[0]["theirs"]
    assert conflicts[0]["theirs"]["items"][0]["food_id"] == food_id


def test_upsert_device_creates_then_updates(db: Session, user: User):
    from app.models.device import Device

    t0 = datetime.now(timezone.utc)
    sync_engine.upsert_device(
        db, user_id=user.id, device_id="dev-1", device_name="Phone", platform="ios", synced_at=t0
    )
    db.commit()
    device = db.query(Device).filter(Device.user_id == user.id, Device.device_id == "dev-1").first()
    assert device is not None
    assert device.device_name == "Phone"

    t1 = t0 + timedelta(minutes=5)
    sync_engine.upsert_device(
        db, user_id=user.id, device_id="dev-1", device_name="Phone Renamed", platform="ios", synced_at=t1
    )
    db.commit()

    devices = db.query(Device).filter(Device.user_id == user.id, Device.device_id == "dev-1").all()
    assert len(devices) == 1
    assert devices[0].device_name == "Phone Renamed"
