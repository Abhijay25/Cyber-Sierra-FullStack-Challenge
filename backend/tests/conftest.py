from __future__ import annotations

import os

# Must be set before any module that reads OPENAI_API_KEY at import time
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from services.db import Base, get_db
from services import session_store

# ── In-memory test database ───────────────────────────────────────────────────
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# query.py uses SessionLocal directly inside the streaming generator (not via
# get_db), so we also patch it there to keep everything on the test DB.
import routers.query as _query_module
_query_module.SessionLocal = TestingSessionLocal

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state():
    """Fresh DB tables and empty session store for every test."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session_store._store.clear()
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)
    session_store._store.clear()
    try:
        from services.limiter import limiter
        limiter._limiter.storage.reset()
    except Exception:
        pass


@pytest.fixture
def client() -> TestClient:
    """Plain client with no session cookie."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def session_client() -> TestClient:
    """Client with a valid session — one CSV sheet already uploaded."""
    with TestClient(app, raise_server_exceptions=True) as c:
        r = c.post(
            "/api/upload",
            files=[("files", ("data.csv", b"name,score\nAlice,95\nBob,87\n", "text/csv"))],
        )
        assert r.status_code == 200
        yield c


SMALL_CSV = b"name,score\nAlice,95\nBob,87\n"
TINY_XLSX_PATH = None  # built lazily in tests that need it
