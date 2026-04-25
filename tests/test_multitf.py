"""Tests for rozkoduj_mcp.tools.multitf."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.multitf import multitf
from tests.conftest import mock_analysis


class TestMultitf:
    """Tests for the multitf MCP tool."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_default_timeframes(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value=mock_analysis("BUY"))

        result = await multitf("BTCUSDT")

        assert len(result["analysis"]) == 5
        assert mock_scanner.analyze.call_count == 5

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_all_buy_alignment(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value=mock_analysis("BUY"))

        result = await multitf("BTCUSDT")

        assert result["alignment"]["direction"] == "BUY"
        assert result["alignment"]["score"] == "5/5"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_mixed_signals(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(
            side_effect=[
                mock_analysis("BUY"),
                mock_analysis("STRONG_BUY"),
                mock_analysis("SELL"),
                mock_analysis("BUY"),
                mock_analysis("NEUTRAL"),
            ]
        )

        result = await multitf("BTCUSDT")

        assert result["alignment"]["direction"] == "BUY"
        assert result["alignment"]["score"] == "3/5"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_custom_timeframes(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value=mock_analysis("SELL"))

        result = await multitf("AAPL", timeframes=["1h", "1d"])

        assert len(result["analysis"]) == 2
        assert result["alignment"]["direction"] == "SELL"
        assert result["alignment"]["score"] == "2/2"

    @pytest.mark.anyio
    async def test_rejects_too_many_timeframes(self) -> None:
        tfs = ["1d"] * 11
        with pytest.raises(ValueError, match="timeframes"):
            await multitf("BTC", timeframes=tfs)  # type: ignore[arg-type]

    @pytest.mark.anyio
    async def test_rejects_long_symbol(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            await multitf("x" * 101)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_strong_buy_maps_to_buy(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(return_value=mock_analysis("STRONG_BUY"))

        result = await multitf("BTCUSDT", timeframes=["1d"])

        assert result["analysis"][0]["direction"] == "BUY"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_partial_failure_drops_failed_timeframes(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(
            side_effect=[
                mock_analysis("BUY"),
                RuntimeError("upstream rate limited"),
                mock_analysis("BUY"),
                RuntimeError("upstream rate limited"),
                mock_analysis("SELL"),
            ]
        )

        result = await multitf("BTCUSDT")

        assert len(result["analysis"]) == 3
        assert len(result["skipped"]) == 2
        assert {entry["timeframe"] for entry in result["skipped"]} == {"1h", "1d"}
        assert result["alignment"]["score"] == "2/3"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.multitf.scanner")
    async def test_all_fail_raises(self, mock_scanner: MagicMock) -> None:
        mock_scanner.analyze = AsyncMock(side_effect=RuntimeError("upstream down"))

        with pytest.raises(RuntimeError, match="No timeframe data available"):
            await multitf("BTCUSDT", timeframes=["1d"])
