from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from models import Prompt
from services.db import get_db

router = APIRouter(tags=["history"])


@router.get("/history")
async def get_history(
    session_id: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Get all prompts for the current session, ordered by created_at descending.

    Requires session_id cookie.
    Returns list of prompts with id, sheet_name, question, answer, feedback, comment, created_at.
    """
    if session_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "session_id cookie is required"},
        )

    # Query all prompts for this session, ordered by created_at descending
    prompts = (
        db.query(Prompt)
        .filter(Prompt.session_id == session_id)
        .order_by(Prompt.created_at.desc())
        .all()
    )

    # Build response
    history = [
        {
            "id": p.id,
            "sheet_name": p.sheet_name,
            "question": p.question,
            "answer": p.answer,
            "feedback": p.feedback,
            "comment": p.comment,
            "created_at": p.created_at.isoformat(),
        }
        for p in prompts
    ]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"history": history},
    )
