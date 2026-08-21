from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import new_uuid
from app.models import Base
from app.models.user import User


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def user(db: Session) -> User:
    u = User(
        id=new_uuid(),
        username="testuser",
        password_hash="x",
        created_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    return u
