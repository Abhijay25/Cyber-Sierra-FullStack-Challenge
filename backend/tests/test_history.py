from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from main import app


async def _fake_format_stream(*args, **kwargs):
    yield "answer"


def _run_query(client: TestClient, question: str = "test?") -> None:
    with patch("routers.query.run_pipeline_compute", new_callable=AsyncMock) as mp, \
         patch("routers.query._openai_format_stream", side_effect=_fake_format_stream):
        mp.return_value = ("refined", "result")
        client.post("/api/query", json={"sheet_name": "data", "question": question})


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_history_no_cookie_returns_401(client: TestClient):
    r = client.get("/api/history")
    assert r.status_code == 401


# ── Isolation ─────────────────────────────────────────────────────────────────

def test_history_empty_for_new_session(session_client: TestClient):
    r = session_client.get("/api/history")
    assert r.status_code == 200
    assert r.json()["history"] == []


def test_history_returns_own_prompts_only(session_client: TestClient):
    _run_query(session_client, "question from session A")

    with TestClient(app, raise_server_exceptions=True) as other:
        other.post(
            "/api/upload",
            files=[("files", ("data.csv", b"name,score\nX,1\n", "text/csv"))],
        )
        _run_query(other, "question from session B")

        r = other.get("/api/history")
        questions = [h["question"] for h in r.json()["history"]]
        assert "question from session B" in questions
        assert "question from session A" not in questions


def test_history_ordered_newest_first(session_client: TestClient):
    _run_query(session_client, "first question")
    _run_query(session_client, "second question")

    r = session_client.get("/api/history")
    questions = [h["question"] for h in r.json()["history"]]
    assert questions[0] == "second question"
    assert questions[1] == "first question"
