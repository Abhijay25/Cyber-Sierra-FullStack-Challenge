from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from models import Prompt, QueryRequest, QueryResponse, Session as SessionModel
from services.ai_pipeline import run_pipeline
from services.db import get_db
from services.session_store import get_sheet

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    session_id: str | None = Cookie(None),
    db: DBSession = Depends(get_db),
) -> QueryResponse:
    """
    Run the AI pipeline against the uploaded sheet.

    Requires session_id cookie.
    Body: QueryRequest(sheet_name, question)
    Returns: QueryResponse(prompt_id, answer)
    """
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_id cookie is required",
        )

    df = get_sheet(session_id, request.sheet_name)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet '{request.sheet_name}' not found for this session",
        )

    # Get preferences from DB; default to empty string
    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )
    preferences_md = session_row.preferences_md if session_row is not None else ""

    refined_prompt, answer = await run_pipeline(request.question, df, preferences_md)

    # Persist the prompt record
    prompt_row = Prompt(
        session_id=session_id,
        sheet_name=request.sheet_name,
        question=request.question,
        refined_prompt=refined_prompt,
        answer=answer,
    )
    db.add(prompt_row)
    db.commit()
    db.refresh(prompt_row)

    return QueryResponse(prompt_id=prompt_row.id, answer=answer)
