"""Tests for rozkoduj_mcp.tools.research."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.research import research


def _mock_result(*, locked: bool) -> dict[str, Any]:
    return {
        "query": "drawdown",
        "articles": [
            {
                "slug": "the-complete-guide-to-algorithmic-trading",
                "locale": "en",
                "title": "The Complete Guide to Algorithmic Trading",
                "description": "Everything you need to know.",
                "chunk_index": 3,
                "chunk_text": "Drawdown is the worst peak-to-trough decline...",
                "parent_text": "Section about backtesting metrics...",
                "context_prefix": "This chunk discusses backtest metrics.",
            }
        ],
        "knowledge": []
        if locked
        else [
            {
                "doc_id": "lessons/risk-101",
                "chunk_index": 0,
                "title": "Risk Lessons 101",
                "chunk_text": "Position sizing matters more than entry timing.",
                "parent_text": None,
                "context_prefix": None,
            }
        ],
        "locked": (
            {
                "fields": ["knowledge"],
                "required_tier": "pro",
                "unlock_url": "https://rozkoduj.com/login",
                "reason": "sign in to include it",
            }
            if locked
            else None
        ),
    }


class TestResearch:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.research.scanner")
    async def test_returns_both_corpora_when_entitled(
        self, mock_scanner: AsyncMock
    ) -> None:
        mock_scanner.search_research = AsyncMock(
            return_value=_mock_result(locked=False)
        )

        result = await research(query="drawdown", locale="en", limit=3)

        mock_scanner.search_research.assert_called_once_with(
            query="drawdown", locale="en", limit=3
        )
        assert result["articles"][0]["slug"].startswith("the-complete")
        assert result["knowledge"][0]["doc_id"] == "lessons/risk-101"
        assert result["locked"] is None

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.research.scanner")
    async def test_anonymous_gets_articles_plus_locked_hint(
        self, mock_scanner: AsyncMock
    ) -> None:
        # The tool has no scope gate - the API decides per tier and returns
        # the locked hint instead of erroring.
        mock_scanner.search_research = AsyncMock(return_value=_mock_result(locked=True))

        result = await research(query="drawdown")

        call = mock_scanner.search_research.call_args
        assert call.kwargs["locale"] is None
        assert call.kwargs["limit"] == 5
        assert result["knowledge"] == []
        assert result["locked"]["fields"] == ["knowledge"]
