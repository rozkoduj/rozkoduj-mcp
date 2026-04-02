"""Tests for rozkoduj_mcp.services.ta."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.services.ta import get_analysis


class TestGetAnalysis:
    """Tests for get_analysis."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.ta.scanner")
    async def test_delegates_to_api(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(
            return_value={"summary": {"recommendation": "BUY"}, "indicators": {"RSI": 42.3}}
        )

        result = await get_analysis("BTCUSDT", "BINANCE", "crypto", "1d")

        mock_scanner.analyze.assert_called_once_with(symbol="BINANCE:BTCUSDT", interval="1d")
        assert result["summary"]["recommendation"] == "BUY"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.ta.scanner")
    async def test_symbol_with_exchange_prefix(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value={"summary": {}, "indicators": {}})

        await get_analysis("BINANCE:BTCUSDT", "", "", "1d")

        mock_scanner.analyze.assert_called_once_with(symbol="BINANCE:BTCUSDT", interval="1d")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.ta.scanner")
    async def test_no_exchange_passes_raw_symbol(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value={"summary": {}, "indicators": {}})

        await get_analysis("BTCUSDT", "", "", "4h")

        mock_scanner.analyze.assert_called_once_with(symbol="BTCUSDT", interval="4h")
