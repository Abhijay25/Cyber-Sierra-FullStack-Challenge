from __future__ import annotations

from fastapi.testclient import TestClient


# ── /api/sheets ───────────────────────────────────────────────────────────────

def test_get_sheets_no_cookie_returns_401(client: TestClient):
    r = client.get("/api/sheets")
    assert r.status_code == 401


def test_get_sheets_returns_metadata(session_client: TestClient):
    r = session_client.get("/api/sheets")
    assert r.status_code == 200
    sheets = r.json()["sheets"]
    assert len(sheets) == 1
    assert sheets[0]["name"] == "data"
    assert sheets[0]["row_count"] == 2


# ── /api/data/{sheet} ─────────────────────────────────────────────────────────

def test_get_data_no_cookie_returns_401(client: TestClient):
    r = client.get("/api/data/anything")
    assert r.status_code == 401


def test_get_data_unknown_sheet_returns_404(session_client: TestClient):
    r = session_client.get("/api/data/nonexistent")
    assert r.status_code == 404


def test_get_data_returns_rows_and_columns(session_client: TestClient):
    r = session_client.get("/api/data/data?n=2")
    assert r.status_code == 200
    body = r.json()
    assert body["columns"] == ["name", "score"]
    assert len(body["rows"]) == 2
    assert body["rows"][0]["name"] == "Alice"


def test_get_data_n_clamped_to_at_least_1(session_client: TestClient):
    r = session_client.get("/api/data/data?n=0")
    assert r.status_code == 200
    assert len(r.json()["rows"]) >= 1


def test_get_data_n_limits_rows(session_client: TestClient):
    r = session_client.get("/api/data/data?n=1")
    assert r.status_code == 200
    assert len(r.json()["rows"]) == 1


# ── DELETE /api/sheets/{sheet} ────────────────────────────────────────────────

def test_delete_sheet_no_cookie_returns_401(client: TestClient):
    r = client.delete("/api/sheets/anything")
    assert r.status_code == 401


def test_delete_sheet_unknown_returns_404(session_client: TestClient):
    r = session_client.delete("/api/sheets/nonexistent")
    assert r.status_code == 404


def test_delete_sheet_removes_it(session_client: TestClient):
    r = session_client.delete("/api/sheets/data")
    assert r.status_code == 200
    assert r.json()["deleted"] == "data"

    r2 = session_client.get("/api/sheets")
    assert r2.json()["sheets"] == []


def test_delete_sheet_data_no_longer_accessible(session_client: TestClient):
    session_client.delete("/api/sheets/data")
    r = session_client.get("/api/data/data")
    assert r.status_code == 404
