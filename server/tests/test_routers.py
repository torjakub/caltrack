"""Router-level tests: exercise the HTTP layer end-to-end with TestClient
against a real (in-memory) database — auth flows, ownership enforcement,
sync push validation, and the timezone day-bucketing logic."""

from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_refresh_token, hash_password
from app.db.base import new_uuid
from app.main import app
from app.models import Base
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    # StaticPool keeps a single connection so the TestClient's worker thread
    # sees the same in-memory database the test fixtures created.
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.services import rate_limit

    rate_limit._attempts.clear()
    yield
    rate_limit._attempts.clear()


@pytest.fixture()
def seeded_user(db_session_factory):
    """A ready-to-login user: username 'alice', password 'password123'.
    Returns the user's id. Reuses an existing row if present (the shared
    module-scoped database outlives individual tests); the ORM instance
    detaches when the session closes, so handing out the object invites
    DetachedInstanceError."""
    session = db_session_factory()
    existing = session.query(User).filter(User.username == "alice").first()
    if existing is not None:
        user_id = existing.id
        session.close()
        return user_id
    user_id = new_uuid()
    session.add(
        User(
            id=user_id,
            username="alice",
            email="alice@example.com",
            password_hash=hash_password("password123"),
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    session.close()
    return user_id


@pytest.fixture()
def client(db_session_factory):
    from app.db.session import get_db

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _auth(client: TestClient, token: str):
    return {"Authorization": f"Bearer {token}"}


class TestSetupAndLogin:
    def test_setup_creates_first_user_and_returns_tokens(self, client):
        res = client.post(
            "/api/v1/auth/setup",
            json={"username": "bob", "password": "password123", "timezone": "UTC"},
        )
        assert res.status_code == 201
        body = res.json()
        assert body["access_token"] and body["refresh_token"]

    def test_second_setup_is_forbidden(self, client, seeded_user):
        res = client.post(
            "/api/v1/auth/setup",
            json={"username": "bob", "password": "password123", "timezone": "UTC"},
        )
        assert res.status_code == 403

    def test_login_with_valid_credentials(self, client, seeded_user):
        res = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_with_wrong_password_is_401(self, client, seeded_user):
        res = client.post("/api/v1/auth/login", json={"username": "alice", "password": "wrong-pass"})
        assert res.status_code == 401

    def test_login_with_unknown_user_is_401(self, client, seeded_user):
        res = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "whatever1"})
        assert res.status_code == 401

    def test_me_requires_token(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401

    def test_me_rejects_garbage_token(self, client):
        res = client.get("/api/v1/auth/me", headers=_auth(client, "not-a-jwt"))
        assert res.status_code == 401


class TestRefresh:
    def test_refresh_returns_new_pair(self, client, seeded_user):
        refresh_token = create_refresh_token(seeded_user)
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        body = res.json()
        assert body["access_token"] and body["refresh_token"]

    def test_access_token_cannot_be_used_as_refresh(self, client, seeded_user):
        login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "password123"})
        access_token = login.json()["access_token"]
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert res.status_code == 401

    def test_garbage_refresh_token_is_401(self, client):
        res = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert res.status_code == 401


class TestOwnership:
    def test_log_endpoints_require_auth(self, client):
        assert client.get("/api/v1/logs", params={"date": "2026-08-24"}).status_code == 401

    def test_custom_food_crud_scoped_to_owner(self, client, db_session_factory, seeded_user):
        # Create a second user to verify isolation.
        other_id = new_uuid()
        session = db_session_factory()
        session.add(
            User(
                id=other_id,
                username="mallory",
                password_hash=hash_password("password123"),
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        session.close()

        alice_token = client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "password123"}
        ).json()["access_token"]
        mallory_token = client.post(
            "/api/v1/auth/login", json={"username": "mallory", "password": "password123"}
        ).json()["access_token"]

        res = client.post(
            "/api/v1/foods",
            headers=_auth(client, alice_token),
            json={
                "name": "Alice's porridge",
                "brand": None,
                "serving_size_g": 100,
                "serving_unit_label": "g",
                "calories_kcal": 100,
                "protein_g": 5,
                "carbs_g": 10,
                "fat_g": 2,
            },
        )
        assert res.status_code == 201, res.text
        food_id = res.json()["id"]

        # Mallory can read it but can't update or delete it.
        assert client.get(f"/api/v1/foods/{food_id}", headers=_auth(client, mallory_token)).status_code == 200
        update = client.put(
            f"/api/v1/foods/{food_id}",
            headers=_auth(client, mallory_token),
            json={
                "name": "Hacked",
                "brand": None,
                "serving_size_g": 1,
                "serving_unit_label": "g",
                "calories_kcal": 1,
                "protein_g": 1,
                "carbs_g": 1,
                "fat_g": 1,
            },
        )
        assert update.status_code == 403
        assert client.delete(f"/api/v1/foods/{food_id}", headers=_auth(client, mallory_token)).status_code == 403

        # The owner can.
        assert (
            client.put(
                f"/api/v1/foods/{food_id}",
                headers=_auth(client, alice_token),
                json={
                    "name": "Alice's porridge v2",
                    "brand": None,
                    "serving_size_g": 100,
                    "serving_unit_label": "g",
                    "calories_kcal": 110,
                    "protein_g": 5,
                    "carbs_g": 10,
                    "fat_g": 2,
                },
            ).status_code
            == 200
        )


class TestSyncPushValidation:
    def _token(self, client, username="alice"):
        return client.post(
            "/api/v1/auth/login", json={"username": username, "password": "password123"}
        ).json()["access_token"]

    def test_push_own_custom_food_applies(self, client, seeded_user):
        token = self._token(client)
        food_id = new_uuid()
        now = datetime.now(timezone.utc).isoformat()
        res = client.post(
            "/api/v1/sync",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "platform": "web",
                "since": None,
                "changes": {
                    "foods": [
                        {
                            "id": food_id,
                            "source": "local",
                            "name": "Custom",
                            "is_custom": True,
                            "created_by_user_id": seeded_user,
                            "updated_at": now,
                        }
                    ]
                },
            },
        )
        assert res.status_code == 200, res.text
        assert res.json()["applied"]["foods"] == [food_id]

    def test_push_non_custom_food_is_422(self, client, seeded_user):
        token = self._token(client)
        res = client.post(
            "/api/v1/sync",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "platform": "web",
                "changes": {
                    "foods": [
                        {
                            "id": new_uuid(),
                            "name": "Not custom",
                            "is_custom": False,
                            "created_by_user_id": seeded_user,
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                },
            },
        )
        assert res.status_code == 422

    def test_push_food_claiming_another_creator_is_422(self, client, seeded_user):
        token = self._token(client)
        res = client.post(
            "/api/v1/sync",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "platform": "web",
                "changes": {
                    "foods": [
                        {
                            "id": new_uuid(),
                            "name": "Stolen",
                            "is_custom": True,
                            "created_by_user_id": new_uuid(),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                },
            },
        )
        assert res.status_code == 422

    def test_push_record_without_id_is_422_not_500(self, client, seeded_user):
        token = self._token(client)
        res = client.post(
            "/api/v1/sync",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "platform": "web",
                "changes": {"log_entries": [{"user_id": seeded_user}]},
            },
        )
        assert res.status_code == 422

    def test_push_record_without_updated_at_is_422(self, client, seeded_user):
        token = self._token(client)
        res = client.post(
            "/api/v1/sync",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "platform": "web",
                "changes": {
                    "log_entries": [{"id": new_uuid(), "user_id": seeded_user, "quantity_g": 50}]
                },
            },
        )
        assert res.status_code == 422

    def test_resolve_with_unknown_entity_type_is_422(self, client, seeded_user):
        token = self._token(client)
        res = client.post(
            "/api/v1/sync/resolve",
            headers=_auth(client, token),
            json={
                "device_id": "dev-test",
                "resolutions": [{"entity_type": "not_a_table", "id": new_uuid(), "resolution": "theirs"}],
            },
        )
        assert res.status_code == 422


class TestTimezoneDayBucketing:
    def test_resolve_log_date_uses_profile_timezone(self):
        from app.routers.logs import _resolve_log_date

        # 23:30 UTC on Aug 24 is already Aug 25 in Tokyo.
        late_evening_utc = datetime(2026, 8, 24, 23, 30, tzinfo=timezone.utc)
        assert _resolve_log_date(late_evening_utc, "Asia/Tokyo") == date(2026, 8, 25)
        # ...and still Aug 24 in New York (UTC-4 in August).
        assert (
            _resolve_log_date(datetime(2026, 8, 24, 20, 0, tzinfo=timezone.utc), "America/New_York")
            == date(2026, 8, 24)
        )

    def test_resolve_log_date_falls_back_on_bad_timezone(self):
        from app.routers.logs import _resolve_log_date

        dt = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
        assert _resolve_log_date(dt, "Not/AZone") == date(2026, 8, 24)

    def test_naive_timestamp_treated_as_utc(self):
        from app.routers.logs import _resolve_log_date

        naive = datetime(2026, 8, 24, 23, 30)  # no tzinfo — server-local/UTC
        assert _resolve_log_date(naive, "Asia/Tokyo") == date(2026, 8, 25)

    def test_day_boundary_near_midnight_offset_by_hours(self):
        from app.routers.logs import _resolve_log_date

        # 01:00 UTC Aug 24 is still Aug 23 in New York (UTC-4).
        early_morning_utc = datetime(2026, 8, 24, 1, 0, tzinfo=timezone.utc)
        assert _resolve_log_date(early_morning_utc, "America/New_York") == date(2026, 8, 23)
