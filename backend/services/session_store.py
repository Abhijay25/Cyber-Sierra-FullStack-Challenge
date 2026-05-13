from __future__ import annotations

import pandas as pd

_store: dict[str, dict[str, pd.DataFrame]] = {}


def set_sheets(session_id: str, sheets: dict[str, pd.DataFrame]) -> None:
    """Store pandas DataFrames for a session, merging with any existing sheets."""
    if session_id not in _store:
        _store[session_id] = {}
    _store[session_id].update(sheets)


def get_sheets(session_id: str) -> dict[str, pd.DataFrame] | None:
    """Retrieve all sheets for a session, or None if session doesn't exist."""
    return _store.get(session_id)


def get_sheet(session_id: str, sheet_name: str) -> pd.DataFrame | None:
    """Retrieve a specific sheet from a session, or None if not found."""
    sheets = _store.get(session_id)
    if sheets is None:
        return None
    return sheets.get(sheet_name)


def get_sheet_meta(session_id: str) -> list[dict]:
    """Return metadata for all sheets in a session.

    Returns a list of dicts with keys: name, row_count, columns.
    Returns empty list if session doesn't exist.
    """
    sheets = _store.get(session_id)
    if sheets is None:
        return []

    meta = []
    for sheet_name, df in sheets.items():
        # Fix D: Cast column names to strings
        meta.append({
            "name": sheet_name,
            "row_count": len(df),
            "columns": [str(c) for c in df.columns],
        })
    return meta
