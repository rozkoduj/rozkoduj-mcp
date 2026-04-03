"""Tests for rozkoduj_mcp.tools.score."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.score import score


def _mock_score_result() -> dict:
    return {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "interval": "1d",
        "score": 78.0,
        "label": "BUY",
        "breakdown": {
            "technical": {"value": 82.0, "weight": 40},
            "momentum": {"value": 71.0, "weight": 25},
            "volume": {"value": 85.0, "weight": 15},
            "trend": {"value": 68.0, "weight": 20},
        },
    }


class TestScore:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.score.scanner")
    async def test_returns_score(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.score = AsyncMock(return_value=_mock_score_result())

        result = await score("AAPL")

        mock_scanner.score.assert_called_once_with("AAPL", "1d")
        assert result["score"] == 78.0
        assert result["label"] == "BUY"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.score.scanner")
    async def test_custom_interval(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.score = AsyncMock(return_value=_mock_score_result())

        await score("BTCUSDT", interval="4h")

        mock_scanner.score.assert_called_once_with("BTCUSDT", "4h")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.score.scanner")
    async def test_has_breakdown(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.score = AsyncMock(return_value=_mock_score_result())

        result = await score("AAPL")

        assert set(result["breakdown"]) == {"technical", "momentum", "volume", "trend"}
