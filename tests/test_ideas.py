"""Tests for rozkoduj_mcp.tools.ideas."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.ideas import ideas


def _mock_result() -> dict:
    return {
        "symbol": "AAPL",
        "total": 100,
        "sentiment": {"long": 7, "short": 2, "neutral": 1, "ratio": 0.78},
        "ideas": [{"title": "AAPL breakout", "direction": "long", "likes": 42}],
    }


class TestIdeas:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.ideas.scanner")
    async def test_returns_ideas(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.ideas = AsyncMock(return_value=_mock_result())

        result = await ideas("AAPL")

        mock_scanner.ideas.assert_called_once_with("AAPL", sort="recent", limit=10)
        assert result["sentiment"]["ratio"] == 0.78

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.ideas.scanner")
    async def test_custom_params(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.ideas = AsyncMock(return_value=_mock_result())

        await ideas("BTCUSD", sort="recent", limit=5)

        mock_scanner.ideas.assert_called_once_with("BTCUSD", sort="recent", limit=5)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.ideas.scanner")
    async def test_clamps_limit(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.ideas = AsyncMock(return_value=_mock_result())

        await ideas("AAPL", limit=999)

        mock_scanner.ideas.assert_called_once_with("AAPL", sort="recent", limit=20)
