from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.db import get_db
from main import app


async def _fake_format_stream(*args, **kwargs):
    yield "answer text"


def _submit_query(client: TestClient) -> int:
    """Helper: run a mocked query and return the prompt_id."""
    import json

    with patch("routers.query.run_pipeline_compute", new_callable=AsyncMock) as mp, \
         patch("routers.query._openai_format_stream", side_effect=_fake_format_stream):
        mp.return_value = ("refined", "42")
        r = client.post(
            "/api/query",
            json={"sheet_name": "data", "question": "test question"},
        )

    for line in r.text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            evt = json.loads(line[6:])
            if evt.get("done"):
                return evt["prompt_id"]

    raise AssertionError("No prompt_id in response")


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_feedback_no_cookie_returns_401(client: TestClient):
    r = client.post("/api/feedback", json={"prompt_id": 1, "feedback": "up"})
    assert r.status_code == 401


# ── Ownership ─────────────────────────────────────────────────────────────────

def test_feedback_cross_session_returns_404(session_client: TestClient):
    prompt_id = _submit_query(session_client)

    # Second independent client with its own session
    with TestClient(app, raise_server_exceptions=True) as other:
        other.post(
            "/api/upload",
            files=[("files", ("x.csv", b"a\n1\n", "text/csv"))],
        )
        r = other.post(
            "/api/feedback",
            json={"prompt_id": prompt_id, "feedback": "up"},
        )
    assert r.status_code == 404


def test_feedback_unknown_prompt_returns_404(session_client: TestClient):
    r = session_client.post(
        "/api/feedback",
        json={"prompt_id": 99999, "feedback": "up"},
    )
    assert r.status_code == 404


# ── Happy paths ───────────────────────────────────────────────────────────────

def test_feedback_upvote_saved(session_client: TestClient):
    prompt_id = _submit_query(session_client)
    r = session_client.post(
        "/api/feedback",
        json={"prompt_id": prompt_id, "feedback": "up"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    history = session_client.get("/api/history").json()["history"]
    assert history[0]["feedback"] == "up"


def test_feedback_downvote_with_comment_saved(session_client: TestClient):
    prompt_id = _submit_query(session_client)

    with patch("routers.feedback.update_preferences", new_callable=AsyncMock) as mock_prefs:
        mock_prefs.return_value = "- Be concise"
        r = session_client.post(
            "/api/feedback",
            json={"prompt_id": prompt_id, "feedback": "down", "comment": "Too verbose"},
        )

    assert r.status_code == 200
    history = session_client.get("/api/history").json()["history"]
    assert history[0]["feedback"] == "down"
    assert history[0]["comment"] == "Too verbose"


# ── Validation ────────────────────────────────────────────────────────────────

def test_feedback_comment_too_long_returns_422(session_client: TestClient):
    r = session_client.post(
        "/api/feedback",
        json={"prompt_id": 1, "feedback": "down", "comment": "x" * 201},
    )
    assert r.status_code == 422
