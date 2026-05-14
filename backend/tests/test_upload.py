from __future__ import annotations

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient


CSV = ("files", ("test.csv", b"a,b\n1,2\n3,4\n", "text/csv"))


def test_upload_csv_returns_sheet_meta(client: TestClient):
    r = client.post("/api/upload", files=[CSV])
    assert r.status_code == 200
    sheets = r.json()["sheets"]
    assert len(sheets) == 1
    assert sheets[0]["name"] == "test"
    assert sheets[0]["row_count"] == 2
    assert "a" in sheets[0]["columns"]


def test_upload_sets_session_cookie(client: TestClient):
    r = client.post("/api/upload", files=[CSV])
    assert r.status_code == 200
    assert "session_id" in r.cookies


def test_upload_reuses_existing_session(client: TestClient):
    r1 = client.post("/api/upload", files=[CSV])
    sid1 = r1.cookies["session_id"]

    r2 = client.post(
        "/api/upload",
        files=[("files", ("other.csv", b"x,y\n1,2\n", "text/csv"))],
    )
    sid2 = r2.cookies["session_id"]
    assert sid1 == sid2


def test_upload_excel_multi_sheet(client: TestClient):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="Sheet1", index=False)
        pd.DataFrame({"b": [3, 4]}).to_excel(writer, sheet_name="Sheet2", index=False)
    buf.seek(0)

    r = client.post(
        "/api/upload",
        files=[("files", (
            "book.xlsx",
            buf.read(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ))],
    )
    assert r.status_code == 200
    names = {s["name"] for s in r.json()["sheets"]}
    assert "book/Sheet1" in names
    assert "book/Sheet2" in names


def test_upload_wrong_extension_rejected(client: TestClient):
    r = client.post(
        "/api/upload",
        files=[("files", ("data.txt", b"hello", "text/plain"))],
    )
    assert r.status_code == 400
    assert "extension" in r.json()["detail"].lower()


def test_upload_wrong_mime_rejected(client: TestClient):
    r = client.post(
        "/api/upload",
        files=[("files", ("data.csv", b"a,b\n1,2\n", "application/octet-stream"))],
    )
    assert r.status_code == 400
    assert "mime" in r.json()["detail"].lower()


def test_upload_empty_file_rejected(client: TestClient):
    r = client.post(
        "/api/upload",
        files=[("files", ("empty.csv", b"", "text/csv"))],
    )
    assert r.status_code == 400


def test_upload_oversized_file_rejected(client: TestClient):
    big = b"a,b\n" + b"1,2\n" * (10 * 1024 * 1024 // 4 + 1)
    r = client.post(
        "/api/upload",
        files=[("files", ("big.csv", big, "text/csv"))],
    )
    assert r.status_code == 413


def test_upload_too_many_files_rejected(client: TestClient):
    files = [("files", (f"f{i}.csv", b"a\n1\n", "text/csv")) for i in range(11)]
    r = client.post("/api/upload", files=files)
    assert r.status_code == 400
    assert "10" in r.json()["detail"]


def test_upload_sheet_cap_enforced(client: TestClient):
    # Upload 15 sheets first
    files = [("files", (f"f{i}.csv", b"a\n1\n", "text/csv")) for i in range(10)]
    r = client.post("/api/upload", files=files)
    assert r.status_code == 200

    files2 = [("files", (f"g{i}.csv", b"a\n1\n", "text/csv")) for i in range(6)]
    r2 = client.post("/api/upload", files=files2)
    assert r2.status_code == 400
    assert "15" in r2.json()["detail"]
