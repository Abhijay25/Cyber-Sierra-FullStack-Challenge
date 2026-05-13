from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from models import FeedbackRequest, Prompt
from services.db import get_db

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    session_id: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Submit feedback on a prompt.

    Requires session_id cookie.
    Body: FeedbackRequest (prompt_id, feedback: 'up'|'down', comment?: str)

    Security: only allow updating prompts owned by the current session.
    Returns 404 if prompt not found.
    Returns 200 with {"ok": true} on success.
    """
    if session_id is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "session_id cookie is required"},
        )

    # Find the prompt by id AND session_id
    prompt = (
        db.query(Prompt)
        .filter(
            Prompt.id == request.prompt_id,
            Prompt.session_id == session_id,
        )
        .first()
    )

    if prompt is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Prompt {request.prompt_id} not found"},
        )

    # Update feedback and comment
    prompt.feedback = request.feedback
    prompt.comment = request.comment
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"ok": True},
    )
