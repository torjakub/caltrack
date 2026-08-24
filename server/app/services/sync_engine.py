"""The sync engine: implements the git-like, whole-record conflict protocol
described in docs/sync-protocol.md. Deliberately not a CRDT/auto-merge
system — conflicts are detected via a single `since` checkpoint per device
and handed back to the user to resolve, never silently overwritten.
"""

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.base import new_uuid
from app.models.device import Device, DevicePlatform
from app.models.food import Food
from app.models.food_micronutrients import FoodMicronutrient
from app.models.food_nutrients import FoodNutrients
from app.models.log_entry import LogEntry
from app.models.recipe import Recipe
from app.models.recipe_item import RecipeItem
from app.models.user_profile import UserProfile
from app.models.user_targets import UserTargets

# Table config: (Model, [settable field names excluding id/updated_at/deleted_at],
# [names of fields that are `date`], [names of fields that are full `datetime`,
# beyond the always-present updated_at/deleted_at])
TABLE_CONFIG: dict[str, tuple[type, list[str], list[str], list[str]]] = {
    "user_profile": (
        UserProfile,
        [
            "user_id",
            "display_name",
            "date_of_birth",
            "sex",
            "height_cm",
            "weight_kg",
            "activity_level",
            "goal",
            "weekly_goal_rate_kg",
            "timezone",
        ],
        ["date_of_birth"],
        [],
    ),
    "user_targets": (
        UserTargets,
        [
            "user_id",
            "effective_date",
            "calories_kcal",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "source",
        ],
        ["effective_date"],
        [],
    ),
    "foods": (
        Food,
        [
            "source",
            "source_id",
            "barcode",
            "name",
            "brand",
            "serving_size_g",
            "serving_unit_label",
            "image_url",
            "is_custom",
            "created_by_user_id",
        ],
        [],
        [],
    ),
    "food_nutrients": (
        FoodNutrients,
        ["food_id", "calories_kcal", "protein_g", "carbs_g", "fat_g"],
        [],
        [],
    ),
    "food_micronutrients": (
        FoodMicronutrient,
        ["food_id", "nutrient_code", "amount_per_100g"],
        [],
        [],
    ),
    "log_entries": (
        LogEntry,
        [
            "user_id",
            "food_id",
            "recipe_id",
            "quantity_g",
            "quantity_servings",
            "meal_type",
            "logged_at",
            "log_date",
            "notes",
        ],
        ["log_date"],
        ["logged_at"],
    ),
}

# Tables where every row must belong to the syncing user — pushed records
# always get user_id force-set to the authenticated user, never trusted
# blindly from the client.
USER_SCOPED_TABLES = {"user_profile", "user_targets", "log_entries"}

NUTRIENT_TABLES = {"food_nutrients", "food_micronutrients"}


class SyncPushError(ValueError):
    """A pushed record violates a server-side invariant (bad shape, or writes
    to rows the client doesn't own). Raised as ValueError so callers treat it
    as an invalid payload; the router maps it to a 422."""


def _require_record_shape(table_name: str, record: dict[str, Any]) -> None:
    if not isinstance(record.get("id"), str) or not record["id"]:
        raise SyncPushError(f"{table_name}: record missing non-empty string 'id'")
    if "updated_at" not in record:
        raise SyncPushError(f"{table_name} {record['id']}: record missing 'updated_at'")


def _validate_food_push(record: dict[str, Any], user_id: str) -> None:
    # Custom foods are the only foods a device ever pushes, and only ones it
    # created for this user (docs/sync-protocol.md). Cached external
    # (OFF/USDA) foods are read-only mirrors of what the server already has.
    # Enforced here rather than trusting the client's dirty-scan scoping.
    if not record.get("is_custom"):
        raise SyncPushError(f"foods {record['id']}: only is_custom=true foods may be pushed")
    if record.get("created_by_user_id") not in (None, user_id):
        raise SyncPushError(
            f"foods {record['id']}: created_by_user_id does not match the authenticated user"
        )


def _validate_existing_food_overwrite(existing: Food, record_id: str, user_id: str) -> None:
    # Never let a push overwrite a row another user owns or a shared cached
    # external food that other users' logs reference.
    if not existing.is_custom or existing.created_by_user_id != user_id:
        raise SyncPushError(
            f"foods {record_id}: refusing to overwrite an existing food this user doesn't own"
        )


def _validate_nutrient_push(db: Session, table_name: str, record: dict[str, Any], user_id: str) -> None:
    food = db.get(Food, record.get("food_id"))
    if food is None:
        raise SyncPushError(f"{table_name} {record['id']}: referenced food does not exist")
    if not food.is_custom or food.created_by_user_id != user_id:
        raise SyncPushError(
            f"{table_name} {record['id']}: nutrients may only be written for this user's own custom foods"
        )


def _parse_value(field: str, value: Any, date_fields: list[str], datetime_fields: list[str]) -> Any:
    if value is None:
        return None
    if field in date_fields:
        return date.fromisoformat(value) if isinstance(value, str) else value
    if field in datetime_fields:
        return _parse_dt(value)
    return value


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """SQLite silently drops tzinfo on DateTime(timezone=True) round-trips —
    values read back from the DB are naive but implicitly UTC. Normalizing
    everything to naive-UTC internally avoids both a naive/aware comparison
    crash and (more importantly) an ambiguous-timestamp bug on the wire: see
    _to_iso, which re-attaches the UTC offset before serializing."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _to_naive_utc(value)
    return _to_naive_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _to_iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _row_to_dict(instance: Any, fields: list[str]) -> dict[str, Any]:
    out = {"id": instance.id, "updated_at": _to_iso(instance.updated_at), "deleted_at": _to_iso(instance.deleted_at)}
    for f in fields:
        out[f] = _to_iso(getattr(instance, f))
    return out


def _apply_simple_table(
    db: Session,
    *,
    table_name: str,
    records: list[dict[str, Any]],
    user_id: str,
    since: datetime | None,
    applied: dict[str, list[str]],
    conflicts: list[dict[str, Any]],
) -> None:
    model, fields, date_fields, datetime_fields = TABLE_CONFIG[table_name]
    for record in records:
        _require_record_shape(table_name, record)
        record_id = record["id"]
        existing = db.get(model, record_id)

        if table_name in USER_SCOPED_TABLES:
            record["user_id"] = user_id

        if table_name == "foods":
            _validate_food_push(record, user_id)
            record["created_by_user_id"] = user_id
            if existing is not None:
                _validate_existing_food_overwrite(existing, record_id, user_id)
        elif table_name in NUTRIENT_TABLES:
            _validate_nutrient_push(db, table_name, record, user_id)

        if existing is None or since is None or existing.updated_at <= since:
            new_updated_at = _parse_dt(record["updated_at"]) or _to_naive_utc(datetime.now(timezone.utc))
            if existing is None:
                instance = model(id=record_id)
                for f in fields:
                    setattr(instance, f, _parse_value(f, record.get(f), date_fields, datetime_fields))
                instance.updated_at = new_updated_at
                instance.deleted_at = _parse_dt(record.get("deleted_at"))
                db.add(instance)
            else:
                for f in fields:
                    if f in record:
                        setattr(existing, f, _parse_value(f, record.get(f), date_fields, datetime_fields))
                existing.updated_at = new_updated_at
                existing.deleted_at = _parse_dt(record.get("deleted_at"))
            applied.setdefault(table_name, []).append(record_id)
        else:
            conflicts.append(
                {
                    "entity_type": table_name,
                    "id": record_id,
                    "mine": record,
                    "theirs": _row_to_dict(existing, fields),
                }
            )


def _apply_recipes(
    db: Session,
    *,
    records: list[dict[str, Any]],
    user_id: str,
    since: datetime | None,
    applied: dict[str, list[str]],
    conflicts: list[dict[str, Any]],
) -> None:
    fields = ["name", "servings", "instructions"]
    for record in records:
        _require_record_shape("recipes", record)
        for item in record.get("items", []):
            if not isinstance(item.get("food_id"), str) or not item["food_id"]:
                raise SyncPushError(f"recipes {record['id']}: item missing 'food_id'")
            if item.get("quantity_g") is None:
                raise SyncPushError(f"recipes {record['id']}: item missing 'quantity_g'")
        record_id = record["id"]
        existing = db.get(Recipe, record_id)
        if existing is not None and existing.user_id != user_id:
            raise SyncPushError(f"recipes {record_id}: refusing to overwrite another user's recipe")
        record["user_id"] = user_id

        if existing is None or since is None or existing.updated_at <= since:
            new_updated_at = _parse_dt(record["updated_at"]) or _to_naive_utc(datetime.now(timezone.utc))
            if existing is None:
                recipe = Recipe(id=record_id, user_id=user_id)
                for f in fields:
                    setattr(recipe, f, record.get(f))
                recipe.updated_at = new_updated_at
                recipe.deleted_at = _parse_dt(record.get("deleted_at"))
                db.add(recipe)
            else:
                for f in fields:
                    if f in record:
                        setattr(existing, f, record.get(f))
                existing.updated_at = new_updated_at
                existing.deleted_at = _parse_dt(record.get("deleted_at"))

            # Items sync as a whole with their parent recipe — replace-all,
            # not independently conflict-checked (see docs/sync-protocol.md).
            db.query(RecipeItem).filter(RecipeItem.recipe_id == record_id).delete()
            for item in record.get("items", []):
                db.add(
                    RecipeItem(
                        id=item.get("id") or new_uuid(),
                        recipe_id=record_id,
                        food_id=item["food_id"],
                        quantity_g=item["quantity_g"],
                    )
                )
            applied.setdefault("recipes", []).append(record_id)
        else:
            existing_items = db.query(RecipeItem).filter(RecipeItem.recipe_id == record_id).all()
            conflicts.append(
                {
                    "entity_type": "recipes",
                    "id": record_id,
                    "mine": record,
                    "theirs": {
                        **_row_to_dict(existing, fields),
                        "items": [
                            {"id": i.id, "food_id": i.food_id, "quantity_g": i.quantity_g} for i in existing_items
                        ],
                    },
                }
            )


PUSH_ORDER = [
    "user_profile",
    "user_targets",
    "foods",
    "food_nutrients",
    "food_micronutrients",
    "recipes",
    "log_entries",
]


def apply_push(
    db: Session, *, changes: dict[str, list[dict[str, Any]]], user_id: str, since: datetime | None
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    since = _to_naive_utc(since)
    applied: dict[str, list[str]] = {}
    conflicts: list[dict[str, Any]] = []

    for table_name in PUSH_ORDER:
        records = changes.get(table_name, [])
        if not records:
            continue
        if table_name == "recipes":
            _apply_recipes(db, records=records, user_id=user_id, since=since, applied=applied, conflicts=conflicts)
        else:
            _apply_simple_table(
                db,
                table_name=table_name,
                records=records,
                user_id=user_id,
                since=since,
                applied=applied,
                conflicts=conflicts,
            )

    return applied, conflicts


def collect_pull(db: Session, *, user_id: str, since: datetime | None) -> dict[str, list[dict[str, Any]]]:
    since = _to_naive_utc(since)

    def changed(model: type, *, extra_filter=None) -> list:
        query = db.query(model).filter(model.user_id == user_id)
        if since is not None:
            query = query.filter(model.updated_at > since)
        if extra_filter is not None:
            query = extra_filter(query)
        return query.all()

    profiles = changed(UserProfile)
    targets = changed(UserTargets)
    log_entries = changed(LogEntry)
    recipes = changed(Recipe)

    referenced_food_ids: set[str] = set()
    for entry in db.query(LogEntry).filter(LogEntry.user_id == user_id, LogEntry.food_id.isnot(None)):
        referenced_food_ids.add(entry.food_id)
    for item in (
        db.query(RecipeItem).join(Recipe, RecipeItem.recipe_id == Recipe.id).filter(Recipe.user_id == user_id)
    ):
        referenced_food_ids.add(item.food_id)

    food_query = db.query(Food).filter(
        (Food.created_by_user_id == user_id) | (Food.id.in_(referenced_food_ids) if referenced_food_ids else False)
    )
    if since is not None:
        food_query = food_query.filter(Food.updated_at > since)
    foods = food_query.all()
    food_ids = [f.id for f in foods]

    nutrients_query = db.query(FoodNutrients).filter(FoodNutrients.food_id.in_(food_ids)) if food_ids else []
    micros_query = (
        db.query(FoodMicronutrient).filter(FoodMicronutrient.food_id.in_(food_ids)) if food_ids else []
    )

    def recipe_to_dict(recipe: Recipe) -> dict[str, Any]:
        items = db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).all()
        return {
            **_row_to_dict(recipe, ["user_id", "name", "servings", "instructions"]),
            "items": [{"id": i.id, "food_id": i.food_id, "quantity_g": i.quantity_g} for i in items],
        }

    return {
        "user_profile": [_row_to_dict(p, TABLE_CONFIG["user_profile"][1]) for p in profiles],
        "user_targets": [_row_to_dict(t, TABLE_CONFIG["user_targets"][1]) for t in targets],
        "foods": [_row_to_dict(f, TABLE_CONFIG["foods"][1]) for f in foods],
        "food_nutrients": [_row_to_dict(n, TABLE_CONFIG["food_nutrients"][1]) for n in nutrients_query],
        "food_micronutrients": [_row_to_dict(m, TABLE_CONFIG["food_micronutrients"][1]) for m in micros_query],
        "recipes": [recipe_to_dict(r) for r in recipes],
        "log_entries": [_row_to_dict(e, TABLE_CONFIG["log_entries"][1]) for e in log_entries],
    }


def upsert_device(
    db: Session, *, user_id: str, device_id: str, device_name: str | None, platform: str, synced_at: datetime
) -> None:
    synced_at = _to_naive_utc(synced_at)
    existing = (
        db.query(Device).filter(Device.user_id == user_id, Device.device_id == device_id).first()
    )
    if existing:
        existing.last_synced_at = synced_at
        existing.last_seen_at = synced_at
        if device_name:
            existing.device_name = device_name
    else:
        db.add(
            Device(
                id=new_uuid(),
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                platform=DevicePlatform(platform),
                last_synced_at=synced_at,
                last_seen_at=synced_at,
            )
        )
