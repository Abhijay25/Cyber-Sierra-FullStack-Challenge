from __future__ import annotations

import json
from urllib.parse import unquote

from fastapi import APIRouter, Cookie, status
from fastapi.responses import JSONResponse

from services import session_store

router = APIRouter(tags=["data"])

MAX_SHEET_NAME_LEN = 255


@router.get("/sheets")
async def get_sheets(session_id: str | None = Cookie(None)) -> JSONResponse:
    """
    Get metadata for all sheets in the current session.

    Requires session_id cookie.
    Returns list of sheet info: name, row_count, columns.
    """
    if session_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "session_id cookie is required"},
        )

    meta = session_store.get_sheet_meta(session_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"sheets": meta},
    )


@router.get("/data/{sheet_name:path}")
async def get_data(
    sheet_name: str,
    session_id: str | None = Cookie(None),
    n: int = 10,
) -> JSONResponse:
    """
    Get rows and columns from a specific sheet.

    Parameters:
    - sheet_name: URL path parameter (will be URL-decoded)
    - session_id: from cookie (required)
    - n: number of rows to return (default 10, max 500)

    Returns rows as list of dicts and columns as list of strings.
    Returns 404 if sheet not found.
    """
    if session_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "session_id cookie is required"},
        )

    sheet_name = unquote(sheet_name)

    if not sheet_name or len(sheet_name) > MAX_SHEET_NAME_LEN:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid sheet name."},
        )

    n = max(1, n)

    # Get sheet
    df = session_store.get_sheet(session_id, sheet_name)
    if df is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Sheet '{sheet_name}' not found"},
        )

    # pandas .to_json handles NaN→null natively; json.loads converts null→None
    rows = json.loads(df.head(n).to_json(orient="records", date_format="iso"))
    # Fix D: Cast column names to strings
    columns = [str(c) for c in df.columns]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "rows": rows,
            "columns": columns,
        },
    )
