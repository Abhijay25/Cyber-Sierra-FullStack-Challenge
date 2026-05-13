from __future__ import annotations

import os
import re
import uuid
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Cookie, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

SECURE_COOKIES = os.getenv("ENVIRONMENT", "development").lower() == "production"

from services import session_store

router = APIRouter(tags=["upload"])

# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS = {".csv", ".xls", ".xlsx"}
ALLOWED_MIMES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload")
async def upload(
    files: list[UploadFile],
    session_id: str | None = Cookie(default=None),
) -> JSONResponse:
    """
    Upload CSV or Excel files and store them in the session.

    Accepts multiple files. For each file:
    - Validates extension (.csv, .xls, .xlsx)
    - Validates MIME type
    - Validates file size (<= 10 MB)
    - Parses and stores DataFrames in session

    Returns sheet metadata (name, row_count, columns).
    Sets session_id cookie if not present.
    """
    # Fix A: Check file count limit
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 files per upload",
        )

    parsed_sheets: dict[str, pd.DataFrame] = {}

    for file in files:
        # Validate file extension
        file_path = Path(file.filename or "")
        file_ext = file_path.suffix.lower()

        if file_ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"File extension '{file_ext}' not allowed. "
                    "Allowed: .csv, .xls, .xlsx"
                },
            )

        # Validate MIME type
        if file.content_type not in ALLOWED_MIMES:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": f"MIME type '{file.content_type}' not allowed. "
                    "Allowed: text/csv, application/vnd.ms-excel, "
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )

        # Read file content
        content = await file.read()

        # Fix B: Check for empty files
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is empty",
            )

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "detail": f"File size exceeds 10 MB limit. "
                    f"Received: {len(content) / 1024 / 1024:.2f} MB"
                },
            )

        # Parse file
        filename_without_ext = file_path.stem
        # Fix C: Sanitize filename
        safe_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', filename_without_ext)

        try:
            if file_ext == ".csv":
                df = pd.read_csv(BytesIO(content))
                parsed_sheets[safe_name] = df
            else:  # .xls or .xlsx
                xls = pd.read_excel(BytesIO(content), sheet_name=None)
                for sheet_name, df in xls.items():
                    key = f"{safe_name}/{sheet_name}"
                    parsed_sheets[key] = df
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"Failed to parse file: {str(e)}"},
            )

    # Use existing session_id if present, otherwise generate new one
    sid = session_id if session_id else str(uuid.uuid4())

    # Store sheets in session
    session_store.set_sheets(sid, parsed_sheets)

    # Get sheet metadata
    meta = session_store.get_sheet_meta(sid)

    # Build response with cookie
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"sheets": meta},
    )

    # Set session_id cookie
    response.set_cookie(
        key="session_id",
        value=sid,
        httponly=True,
        samesite="strict",
        secure=SECURE_COOKIES,
        max_age=86400,  # 24 hours
        path="/",
    )

    return response
