from __future__ import annotations

import time

import pandas as pd

SESSION_TTL = 86400  # 24 hours in seconds

# { session_id → { "sheets": { sheet_name → DataFrame }, "last_access": float } }
_store: dict[str, dict] = {}


def _touch(session_id: str) -> None:
    if session_id in _store:
        _store[session_id]["last_access"] = time.monotonic()


def _evict_stale() -> None:
    cutoff = time.monotonic() - SESSION_TTL
    stale = [sid for sid, v in _store.items() if v["last_access"] < cutoff]
    for sid in stale:
        del _store[sid]


def set_sheets(session_id: str, sheets: dict[str, pd.DataFrame]) -> None:
    _evict_stale()
    if session_id not in _store:
        _store[session_id] = {"sheets": {}, "last_access": time.monotonic()}
    _store[session_id]["sheets"].update(sheets)
    _store[session_id]["last_access"] = time.monotonic()


def get_sheets(session_id: str) -> dict[str, pd.DataFrame] | None:
    _touch(session_id)
    entry = _store.get(session_id)
    return entry["sheets"] if entry else None


def get_sheet(session_id: str, sheet_name: str) -> pd.DataFrame | None:
    _touch(session_id)
    entry = _store.get(session_id)
    if entry is None:
        return None
    return entry["sheets"].get(sheet_name)


def get_sheet_meta(session_id: str) -> list[dict]:
    _touch(session_id)
    entry = _store.get(session_id)
    if entry is None:
        return []
    return [
        {
            "name": name,
            "row_count": len(df),
            "columns": [str(c) for c in df.columns],
        }
        for name, df in entry["sheets"].items()
    ]
