"""Test fixtures. Use an in-memory SQLite for unit-level service tests and a
disposable Postgres (via DATABASE_URL_TEST env) for the integration tests.
The JSONB + PG_UUID column types are incompatible with SQLite in strict mode,
so we only use SQLite for pure Python service tests that don't touch those
columns directly — schema-sensitive tests skip if Postgres isn't available.
"""

from __future__ import annotations

import os
import uuid
from typing import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="session")
def pg_url() -> str | None:
    return os.environ.get("DATABASE_URL_TEST")


@pytest.fixture
def pg_session(pg_url) -> Iterator[Session]:
    if not pg_url:
        pytest.skip("DATABASE_URL_TEST not set — skipping integration test")
    # Lazy imports so pure unit tests don't require these packages loaded
    from app.core.database import Base
    import app.models  # noqa: F401

    engine = create_engine(pg_url, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    db = Session_()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def demo_org_id() -> uuid.UUID:
    return uuid.uuid4()
