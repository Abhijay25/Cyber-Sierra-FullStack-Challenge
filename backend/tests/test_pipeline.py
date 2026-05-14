from __future__ import annotations

"""Unit tests for the AI pipeline logic — no real OpenAI or PandasAI calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from services.ai_pipeline import (
    _NOT_APPLICABLE,
    _openai_format_stream,
    run_pipeline_compute,
)


DF = pd.DataFrame({"name": ["Alice", "Bob"], "score": [95, 87]})
COLUMNS = ["name", "score"]


# ── Relevance gate (sentinel short-circuit) ───────────────────────────────────

@pytest.mark.asyncio
async def test_not_applicable_sentinel_short_circuits_pipeline():
    """When rewrite returns the sentinel, PandasAI should never be called."""
    sentinel_response = f"{_NOT_APPLICABLE} 'salary' column does not exist"

    with patch("services.ai_pipeline._openai_rewrite", new_callable=AsyncMock) as mock_rewrite, \
         patch("services.ai_pipeline._run_pandasai") as mock_pandas:
        mock_rewrite.return_value = sentinel_response

        refined, raw = await run_pipeline_compute(
            question="what is the average salary?",
            df=DF,
            preferences_md="",
            history=[],
        )

    mock_pandas.assert_not_called()
    assert refined.startswith(_NOT_APPLICABLE)
    assert raw.startswith(_NOT_APPLICABLE)


@pytest.mark.asyncio
async def test_format_stream_yields_friendly_message_for_sentinel():
    """The format step converts the sentinel into a readable rejection."""
    raw = f"{_NOT_APPLICABLE} 'salary' column does not exist"
    tokens = []
    async for token in _openai_format_stream(raw, "what is salary?", "", []):
        tokens.append(token)

    full = "".join(tokens)
    assert "salary" in full.lower() or "dataset" in full.lower()
    assert _NOT_APPLICABLE not in full


# ── Fallback chain ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pandasai_failure_triggers_context_stuffing_for_small_df():
    """PandasAI failure on a ≤100-row DF should fall back to context stuffing."""
    small_df = DF.copy()

    with patch("services.ai_pipeline._openai_rewrite", new_callable=AsyncMock) as mock_rewrite, \
         patch("services.ai_pipeline._run_pandasai", side_effect=RuntimeError("fail")), \
         patch("services.ai_pipeline._openai_context_stuffing", new_callable=AsyncMock) as mock_stuffing:
        mock_rewrite.return_value = "return df['score'].mean()"
        mock_stuffing.return_value = "The mean score is 91."

        _, raw = await run_pipeline_compute(
            question="what is the average score?",
            df=small_df,
            preferences_md="",
            history=[],
        )

    mock_stuffing.assert_called_once()
    assert raw == "The mean score is 91."


@pytest.mark.asyncio
async def test_pandasai_failure_on_large_df_retries_with_simplified_prompt():
    """PandasAI failure on a >100-row DF should retry with a simplified prompt."""
    large_df = pd.DataFrame({"score": range(150)})

    with patch("services.ai_pipeline._openai_rewrite", new_callable=AsyncMock) as mock_rewrite, \
         patch("services.ai_pipeline._run_pandasai", side_effect=[RuntimeError("fail"), "75.0"]) as mock_pandas, \
         patch("services.ai_pipeline._simplify_prompt", new_callable=AsyncMock) as mock_simplify:
        mock_rewrite.return_value = "return df['score'].mean()"
        mock_simplify.return_value = "mean of score column"

        _, raw = await run_pipeline_compute(
            question="average?",
            df=large_df,
            preferences_md="",
            history=[],
        )

    assert mock_pandas.call_count == 2
    assert raw == "75.0"
