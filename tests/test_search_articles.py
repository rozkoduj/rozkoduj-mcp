"""Tests for rozkoduj_mcp.tools.search_articles."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.search_articles import search_articles


def _mock_result() -> dict[str, Any]:
    return {
        "query": "drawdown",
        "items": [
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
    }


class TestSearchArticles:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_articles.scanner")
    async def test_returns_results(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_articles = AsyncMock(return_value=_mock_result())

        result = await search_articles(query="drawdown", locale="en", limit=3)

        mock_scanner.search_articles.assert_called_once_with(
            query="drawdown", locale="en", limit=3
        )
        assert result == _mock_result()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_articles.scanner")
    async def test_locale_optional(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_articles = AsyncMock(return_value={"query": "q", "items": []})

        await search_articles(query="q")

        call = mock_scanner.search_articles.call_args
        assert call.kwargs["locale"] is None
        assert call.kwargs["limit"] == 5

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.search_articles.scanner")
    async def test_limit_clamped(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.search_articles = AsyncMock(return_value={"query": "q", "items": []})

        await search_articles(query="q", limit=999)

        assert mock_scanner.search_articles.call_args.kwargs["limit"] == 20
