from __future__ import annotations

import re

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from models import Prompt, QueryRequest, QueryResponse, Session as SessionModel
from services.ai_pipeline import run_pipeline
from services.db import get_db
from services.limiter import limiter
from services.session_store import get_sheet

router = APIRouter(tags=["query"])

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
MAX_QUESTION_LEN = 1000


def _sanitise_question(raw: str) -> str:
    """Strip control characters and enforce length limit."""
    cleaned = _CONTROL_CHARS.sub('', raw).strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )
    if len(cleaned) > MAX_QUESTION_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question exceeds {MAX_QUESTION_LEN} character limit.",
        )
    return cleaned


@router.post("/query", response_model=QueryResponse)
@limiter.limit("20/minute")
async def query(
    http_request: Request,
    request: QueryRequest,
    session_id: str | None = Cookie(None),
    db: DBSession = Depends(get_db),
) -> QueryResponse:
    """
    Run the AI pipeline against the uploaded sheet.

    Rate limited: 20 requests/minute per IP.
    Requires session_id cookie.
    Body: QueryRequest(sheet_name, question, n?, history[])
    Returns: QueryResponse(prompt_id, answer)
    """
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_id cookie is required",
        )

    question = _sanitise_question(request.question)

    df = get_sheet(session_id, request.sheet_name)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet '{request.sheet_name}' not found for this session",
        )

    if request.n is not None:
        df = df.head(max(1, request.n))

    session_row = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )
    preferences_md = session_row.preferences_md if session_row is not None else ""

    history = [{"question": t.question, "answer": t.answer} for t in request.history]
    refined_prompt, answer = await run_pipeline(question, df, preferences_md, history)

    prompt_row = Prompt(
        session_id=session_id,
        sheet_name=request.sheet_name,
        question=question,
        refined_prompt=refined_prompt,
        answer=answer,
    )
    db.add(prompt_row)
    db.commit()
    db.refresh(prompt_row)

    return QueryResponse(prompt_id=prompt_row.id, answer=answer)
