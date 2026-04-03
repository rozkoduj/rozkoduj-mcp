"""Tests for rozkoduj_mcp.tools.analyze."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.analyze import analyze
from tests.conftest import mock_analysis


class TestAnalyze:
    """Tests for the analyze MCP tool."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.analyze.ta_service")
    async def test_returns_analysis(self, mock_ta: MagicMock) -> None:
        mock_ta.get_analysis = AsyncMock(return_value=mock_analysis())

        result = await analyze("BTCUSDT")

        mock_ta.get_analysis.assert_called_once_with("BTCUSDT", "1d")
        assert result["summary"]["recommendation"] == "BUY"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.analyze.ta_service")
    async def test_custom_interval(self, mock_ta: MagicMock) -> None:
        mock_ta.get_analysis = AsyncMock(return_value=mock_analysis())

        await analyze("AAPL", interval="4h")

        mock_ta.get_analysis.assert_called_once_with("AAPL", "4h")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.analyze.ta_service")
    async def test_result_has_indicators(self, mock_ta: MagicMock) -> None:
        mock_ta.get_analysis = AsyncMock(return_value=mock_analysis())

        result = await analyze("ETHUSDT")

        assert "indicators" in result
        assert result["indicators"]["RSI"] == 42.3
