"""Tests for rozkoduj_mcp.tools.compare."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.compare import compare
from tests.conftest import mock_analysis


class TestCompare:
    """Tests for the compare MCP tool."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.compare.scanner")
    async def test_multi_symbol(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(
            side_effect=[mock_analysis("BUY", 42.3), mock_analysis("SELL", 72.1)]
        )

        result = await compare(["BTCUSDT", "ETHUSDT"])

        assert len(result) == 2
        assert result[0]["recommendation"] == "BUY"
        assert result[0]["rsi"] == 42.3
        assert result[1]["recommendation"] == "SELL"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.compare.scanner")
    async def test_result_keys(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value=mock_analysis())

        result = await compare(["BTCUSDT"])

        expected_keys = {
            "symbol",
            "exchange",
            "recommendation",
            "rsi",
            "macd",
            "macd_signal",
            "adx",
            "oscillators",
            "moving_averages",
        }
        assert set(result[0].keys()) == expected_keys

    @pytest.mark.anyio
    async def test_too_many_symbols(self) -> None:
        symbols = [f"SYM{i}" for i in range(11)]
        with pytest.raises(ValueError, match="at most 10"):
            await compare(symbols)

    @pytest.mark.anyio
    async def test_empty_symbols(self) -> None:
        with pytest.raises(ValueError, match="at least 1"):
            await compare([])

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.compare.scanner")
    async def test_partial_failure_marks_failed_symbols(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(
            side_effect=[
                mock_analysis("BUY"),
                RuntimeError("upstream rate limited"),
                mock_analysis("SELL"),
            ]
        )

        result = await compare(["BTCUSDT", "ETHUSDT", "SOLUSDT"])

        assert len(result) == 3
        assert result[0]["recommendation"] == "BUY"
        assert result[1] == {"symbol": "ETHUSDT", "error": "upstream_unavailable"}
        assert result[2]["recommendation"] == "SELL"
