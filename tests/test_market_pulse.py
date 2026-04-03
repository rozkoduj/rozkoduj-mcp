"""Tests for rozkoduj_mcp.tools.market_pulse."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.market_pulse import market_pulse


def _mock_result() -> dict:
    return {
        "verdict": "RISK-OFF",
        "stocks": {"score": 19.3, "label": "EXTREME_FEAR"},
        "crypto": {"score": 9.0, "label": "Extreme Fear"},
        "vix": 24.5,
    }


class TestMarketPulse:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.market_pulse.scanner")
    async def test_returns_regime(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.market_pulse = AsyncMock(return_value=_mock_result())

        result = await market_pulse()

        mock_scanner.market_pulse.assert_called_once()
        assert result["verdict"] == "RISK-OFF"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.market_pulse.scanner")
    async def test_has_all_sections(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.market_pulse = AsyncMock(return_value=_mock_result())

        result = await market_pulse()

        assert set(result) == {"verdict", "stocks", "crypto", "vix"}
