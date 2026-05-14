from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def parse_sse(text: str) -> list[dict]:
    events = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


async def _fake_format_stream(*args, **kwargs):
    yield "The answer is "
    yield "42."


# ── Auth & routing ────────────────────────────────────────────────────────────

def test_query_no_cookie_returns_401(client: TestClient):
    r = client.post("/api/query", json={"sheet_name": "data", "question": "hello"})
    assert r.status_code == 401


def test_query_unknown_sheet_returns_404(session_client: TestClient):
    with patch("routers.query.run_pipeline_compute", new_callable=AsyncMock) as mock_pipeline, \
         patch("routers.query._openai_format_stream", side_effect=_fake_format_stream):
        mock_pipeline.return_value = ("refined", "42")
        r = session_client.post(
            "/api/query",
            json={"sheet_name": "nonexistent", "question": "hello"},
        )
    assert r.status_code == 404


# ── Input sanitisation ────────────────────────────────────────────────────────

def test_query_empty_question_returns_400(session_client: TestClient):
    r = session_client.post("/api/query", json={"sheet_name": "data", "question": ""})
    assert r.status_code == 400


def test_query_whitespace_only_question_returns_400(session_client: TestClient):
    r = session_client.post("/api/query", json={"sheet_name": "data", "question": "   "})
    assert r.status_code == 400


def test_query_too_long_question_returns_400(session_client: TestClient):
    r = session_client.post(
        "/api/query",
        json={"sheet_name": "data", "question": "a" * 1001},
    )
    assert r.status_code == 400


# ── Happy path (mocked pipeline) ─────────────────────────────────────────────

def test_query_streams_tokens_and_prompt_id(session_client: TestClient):
    with patch("routers.query.run_pipeline_compute", new_callable=AsyncMock) as mock_pipeline, \
         patch("routers.query._openai_format_stream", side_effect=_fake_format_stream):
        mock_pipeline.return_value = ("refined", "42")
        r = session_client.post(
            "/api/query",
            json={"sheet_name": "data", "question": "What is the highest score?"},
        )

    assert r.status_code == 200
    events = parse_sse(r.text)

    tokens = [e["token"] for e in events if "token" in e]
    assert "".join(tokens) == "The answer is 42."

    done_events = [e for e in events if e.get("done")]
    assert len(done_events) == 1
    assert isinstance(done_events[0]["prompt_id"], int)


def test_query_saves_prompt_to_history(session_client: TestClient):
    with patch("routers.query.run_pipeline_compute", new_callable=AsyncMock) as mock_pipeline, \
         patch("routers.query._openai_format_stream", side_effect=_fake_format_stream):
        mock_pipeline.return_value = ("refined", "42")
        session_client.post(
            "/api/query",
            json={"sheet_name": "data", "question": "What is the highest score?"},
        )

    r = session_client.get("/api/history")
    history = r.json()["history"]
    assert len(history) == 1
    assert history[0]["question"] == "What is the highest score?"
    assert history[0]["answer"] == "The answer is 42."
