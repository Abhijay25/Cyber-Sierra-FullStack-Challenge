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
            max_tokens=1000,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_NOT_APPLICABLE = "__NOT_APPLICABLE__:"


async def _openai_rewrite(
    question: str,
    columns: list[str],
    preferences_md: str,
    history: list[dict[str, str]],
) -> str:
    """Step 1: Rewrite the question as a precise pandas-friendly instruction.

    Returns a string starting with _NOT_APPLICABLE if the question cannot be
    answered from the available columns (off-topic, nonexistent column, nonsense).
    """
    column_list = ", ".join(columns)
    prefs_section = f"\nUser preferences to apply:\n{preferences_md}" if preferences_md else ""
    system_prompt = (
        f"You are a data analysis assistant. The DataFrame has these columns: {column_list}.\n"
        f"Decide whether the user's question can be answered from these columns, then:\n"
        f"\n"
        f"IF answerable from the data:\n"
        f"- Rewrite as a minimal, precise pandas instruction naming the exact column(s) and operation.\n"
        f"- If the answer is a single number, say 'return a single scalar value'.\n"
        f"- Do NOT add distributions, groupings, or percentages unless the user explicitly asked.\n"
        f"- Do NOT map unrelated concepts to existing columns "
        f"  (e.g. 'salary' is NOT 'Fare', 'dragons' is not a real column).\n"
        f"- Use prior conversation turns only to resolve pronouns like 'that', 'it', 'those'.\n"
        f"\n"
        f"IF NOT answerable (question is off-topic, references a column that doesn't exist, "
        f"or is nonsensical with respect to this dataset):\n"
        f"- Respond EXACTLY: {_NOT_APPLICABLE} <short specific reason — name what's missing or why it's off-topic; do NOT say 'cannot be answered from the dataset'>\n"
        f"\n"
        f"Return ONLY the pandas instruction OR the {_NOT_APPLICABLE} line. No code, no extra text."
        f"{prefs_section}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in history[-5:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})
    messages.append({"role": "user", "content": question})

    response = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,  # type: ignore[arg-type]
        max_tokens=200,
    )
    content = response.choices[0].message.content
    return content.strip() if content else question


# ---------------------------------------------------------------------------
# PandasAI agent cache — keyed on (session_id, sheet_name, df_row_count)
# so a new agent is only created when the session, sheet, or analysed row
# count changes. Cleared when files are re-uploaded or a session is evicted.
# ---------------------------------------------------------------------------

_agent_cache: dict[tuple[str, str, int], object] = {}


def clear_session_agents(session_id: str) -> None:
    stale = [k for k in _agent_cache if k[0] == session_id]
    for k in stale:
        del _agent_cache[k]


def _get_or_create_agent(session_id: str, sheet_name: str, df: pd.DataFrame) -> object:
    from pandasai import Agent

    key = (session_id, sheet_name, len(df))
    if key not in _agent_cache:
        llm = _OpenAIAdapter(api_key=OPENAI_API_KEY)
        _agent_cache[key] = Agent([df], config={"llm": llm})
    return _agent_cache[key]


def _run_pandasai(session_id: str, sheet_name: str, df: pd.DataFrame, prompt: str) -> str:
    """Run PandasAI Agent synchronously, reusing a cached agent. Called via asyncio.to_thread."""
    agent = _get_or_create_agent(session_id, sheet_name, df)
    result = agent.chat(prompt)  # type: ignore[union-attr]
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


async def _openai_format_stream(
    raw_result: str,
    question: str,
    preferences_md: str,
    history: list[dict[str, str]],
):
    """Step 2.5: Stream the formatted answer token by token."""
    if raw_result.startswith(_NOT_APPLICABLE):
        reason = raw_result[len(_NOT_APPLICABLE):].strip()
        yield f"This dataset doesn't contain that information — {reason}"
        return

    prefs_section = (
        f"\n\nApply these user style preferences to your answer:\n{preferences_md}"
        if preferences_md else ""
    )
    system_prompt = (
        "You are a data analysis assistant. Present the result as a short, "
        "direct answer (2-4 sentences). Do not invent data not present in the result."
        f"{prefs_section}"
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for turn in history[-5:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})
    messages.append({"role": "user", "content": f"Question: {question}\nResult: {raw_result}"})

    stream = await _get_async_client().chat.completions.create(
        model="gpt-4o",
        messages=messages,  # type: ignore[arg-type]
        max_tokens=300,
        stream=True,
    )
    async for chunk in stream:
        token = chunk.choices[0].delta.content
        if token:
            yield token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def run_pipeline_compute(
    question: str,
    df: pd.DataFrame,
    preferences_md: str,
    history: list[dict[str, str]] | None = None,
    session_id: str = "",
    sheet_name: str = "",
) -> tuple[str, str]:
    """
    Steps 1 and 2 of the pipeline: rewrite + PandasAI execution.

    Returns (refined_prompt, raw_result). The caller streams the format step.
    """
    hist = history or []
    columns = [str(c) for c in df.columns.tolist()]

    refined_prompt = await _openai_rewrite(question, columns, preferences_md, hist)
    logger.info("Refined prompt: %s", refined_prompt)

    if refined_prompt.startswith(_NOT_APPLICABLE):
        reason = refined_prompt[len(_NOT_APPLICABLE):].strip()
        return refined_prompt, f"{_NOT_APPLICABLE} {reason}"

    try:
        raw_result = await asyncio.to_thread(_run_pandasai, session_id, sheet_name, df, refined_prompt)
    except Exception:
        logger.exception("PandasAI failed")
        if len(df) <= 100:
            raw_result = await _openai_context_stuffing(refined_prompt, df, preferences_md)
        else:
            simplified = await _simplify_prompt(question, columns)
            try:
                raw_result = await asyncio.to_thread(_run_pandasai, session_id, sheet_name, df, simplified)
            except Exception:
                logger.exception("PandasAI failed on simplified prompt")
                raw_result = "Could not compute an answer for this question."

    return refined_prompt, str(raw_result)


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
