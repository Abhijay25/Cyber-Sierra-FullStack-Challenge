from __future__ import annotations

import json
import re

from fastapi import APIRouter, Cookie, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from models import Prompt, Session as SessionModel, QueryRequest
from services.ai_pipeline import run_pipeline_compute, _openai_format_stream
from services.db import SessionLocal
from services.limiter import limiter
from services.session_store import get_sheet

router = APIRouter(tags=["query"])

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
MAX_QUESTION_LEN = 1000
MAX_SHEET_NAME_LEN = 255


def _sanitise_question(raw: str) -> str:
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


def _validate_sheet_name(name: str) -> None:
    if not name or len(name) > MAX_SHEET_NAME_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sheet name.",
        )


@router.post("/query")
@limiter.limit("20/minute")
async def query(
    http_request: Request,
    request: QueryRequest,
    session_id: str | None = Cookie(None),
) -> StreamingResponse:
    """
    Run the AI pipeline against the uploaded sheet, streaming the answer.

    Rate limited: 20 requests/minute per IP.
    Requires session_id cookie.
    Returns a text/event-stream of {"token": str} events, ending with {"done": true, "prompt_id": int}.
    """
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session_id cookie is required",
        )

    _validate_sheet_name(request.sheet_name)
    question = _sanitise_question(request.question)

    df = get_sheet(session_id, request.sheet_name)
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sheet '{request.sheet_name}' not found for this session",
        )

    if request.n is not None:
        df = df.head(max(1, request.n))

    # Read preferences before streaming starts
    with SessionLocal() as db:
        session_row = (
            db.query(SessionModel)
            .filter(SessionModel.session_id == session_id)
            .first()
        )
        preferences_md = session_row.preferences_md if session_row is not None else ""

    history = [{"question": t.question, "answer": t.answer} for t in request.history]

    async def generate():
        try:
            refined_prompt, raw_result = await run_pipeline_compute(
                question, df, preferences_md, history
            )

            full_answer = ""
            async for token in _openai_format_stream(raw_result, question, preferences_md, history):
                full_answer += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Persist after streaming completes
            with SessionLocal() as db:
                prompt_row = Prompt(
                    session_id=session_id,
                    sheet_name=request.sheet_name,
                    question=question,
                    refined_prompt=refined_prompt,
                    answer=full_answer,
                )
                db.add(prompt_row)
                db.commit()
                db.refresh(prompt_row)
                prompt_id = prompt_row.id

            yield f"data: {json.dumps({'done': True, 'prompt_id': prompt_id})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
