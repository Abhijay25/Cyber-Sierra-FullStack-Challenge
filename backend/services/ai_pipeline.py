from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import openai
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy.orm import Session as DBSession

load_dotenv()

OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY") or ""
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set")

logger = logging.getLogger(__name__)

_async_client: openai.AsyncOpenAI | None = None


def _get_async_client() -> openai.AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY, timeout=30.0)
    return _async_client

# ---------------------------------------------------------------------------
# PandasAI v3 custom LLM adapter (synchronous, wraps openai.OpenAI)
# ---------------------------------------------------------------------------

from pandasai.agent.state import AgentState
from pandasai.core.prompts.base import BasePrompt
from pandasai.llm.base import LLM


class _OpenAIAdapter(LLM):
    """Synchronous OpenAI adapter for PandasAI v3."""

    _type: str = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        super().__init__(api_key=api_key)
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    @property
    def type(self) -> str:
        return self._type

    def call(self, instruction: BasePrompt, context: Optional[AgentState] = None) -> str:
        prompt_text = instruction.to_string()
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=500,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _openai_rewrite(question: str, columns: list[str], preferences_md: str) -> str:
    """Step 1: Rewrite the question as a precise pandas-friendly instruction."""
    column_list = ", ".join(columns)
    prefs_section = f"\nUser preferences to apply:\n{preferences_md}" if preferences_md else ""
    system_prompt = (
        f"You are a data analysis assistant. Rewrite the user's question as a precise, "
        f"pandas-friendly instruction for a DataFrame with columns: {column_list}.\n"
        f"Return ONLY the rewritten instruction, nothing else."
        f"{prefs_section}"
    )
    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        max_tokens=200,
    )
    content = response.choices[0].message.content
    return content.strip() if content else question


def _run_pandasai(df: pd.DataFrame, prompt: str) -> str:
    """Run PandasAI Agent synchronously. Called via asyncio.to_thread."""
    from pandasai import Agent

    llm = _OpenAIAdapter(api_key=OPENAI_API_KEY)
    agent = Agent([df], config={"llm": llm})
    result = agent.chat(prompt)
    return str(result)


async def _simplify_prompt(question: str, columns: list[str]) -> str:
    """Cheap OpenAI call to strip conversational framing into a direct computation."""
    col_str = ", ".join(columns)
    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Rewrite as a single direct pandas computation: {question}, "
                    f"columns: {col_str}. One sentence only."
                ),
            }
        ],
        max_tokens=80,
    )
    content = response.choices[0].message.content
    return content.strip() if content else question


async def _openai_context_stuffing(
    prompt: str, df: pd.DataFrame, preferences_md: str
) -> str:
    """Step 3a: Send top-100 rows as CSV to OpenAI when PandasAI fails on small DF."""
    csv_str = df.head(100).to_csv(index=False)
    # Truncate to max 8000 chars to stay within token limits
    csv_str = csv_str[:8000]
    prefs_section = f"\nUser preferences:\n{preferences_md}" if preferences_md else ""
    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data analysis assistant. Answer the user's question "
                    f"using the CSV data provided below.{prefs_section}"
                ),
            },
            {
                "role": "user",
                "content": f"Data:\n{csv_str}\n\nQuestion: {prompt}",
            },
        ],
        max_tokens=500,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Could not compute an answer for this question."


async def _openai_format(raw_result: str, question: str, preferences_md: str) -> str:
    """Step 2.5: Format the raw result into a clear, concise answer."""
    prefs_section = (
        f"\n\nApply these user style preferences to your answer:\n{preferences_md}"
        if preferences_md else ""
    )
    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a data analysis assistant. Present the result as a short, "
                    "direct answer (2-4 sentences). Do not invent data not present in the result."
                    f"{prefs_section}"
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\nResult: {raw_result}",
            },
        ],
        max_tokens=300,
    )
    content = response.choices[0].message.content
    return content.strip() if content else raw_result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_pipeline(
    question: str,
    df: pd.DataFrame,
    preferences_md: str,
) -> tuple[str, str]:
    """
    Full AI query pipeline.

    Returns (refined_prompt, answer).
    """
    columns = [str(c) for c in df.columns.tolist()]

    # Step 1 — Reformulate question via OpenAI
    refined_prompt = await _openai_rewrite(question, columns, preferences_md)

    # Step 2 — PandasAI execution (sync, wrapped in thread)
    raw_result: Optional[str] = None
    try:
        raw_result = await asyncio.to_thread(_run_pandasai, df, refined_prompt)
    except Exception:
        logger.exception("PandasAI failed")
        # Fallback logic
        if len(df) <= 100:
            # Step 3a: context stuffing
            raw_result = await _openai_context_stuffing(refined_prompt, df, preferences_md)
        else:
            # Step 3b: retry with simplified prompt
            simplified = await _simplify_prompt(question, columns)
            try:
                raw_result = await asyncio.to_thread(_run_pandasai, df, simplified)
            except Exception:
                logger.exception("PandasAI failed on simplified prompt")
                return refined_prompt, "Could not compute an answer for this question."

    # Step 2.5 — Formatting pass
    answer = await _openai_format(raw_result, question, preferences_md)
    return refined_prompt, answer


async def update_preferences(
    session_id: str,
    comment: str,
    current_preferences_md: str,
    db: DBSession,
) -> str:
    """
    Called on downvote+comment. Merges feedback into the preferences markdown.
    Saves updated preferences to the Session table. Returns the updated markdown.
    """
    from models import Session as SessionModel

    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You maintain a concise user preferences list for AI data analysis responses. "
                    "Merge the new feedback into the existing list as short, actionable bullet points. "
                    "Rules: each bullet is one clear instruction (e.g. '- Always include percentage breakdowns'). "
                    "Max 8 bullets total. No headers, no explanations, no examples — bullets only. "
                    "Return ONLY the updated bullet list."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Current preferences:\n{current_preferences_md or '(none yet)'}\n\n"
                    f"New feedback: {comment}"
                ),
            },
        ],
        max_tokens=200,
    )
    content = response.choices[0].message.content
    updated_md = content.strip() if content else current_preferences_md

    # Upsert Session row
    session_row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if session_row is None:
        session_row = SessionModel(session_id=session_id, preferences_md=updated_md)
        db.add(session_row)
    else:
        session_row.preferences_md = updated_md
    db.commit()

    return updated_md
