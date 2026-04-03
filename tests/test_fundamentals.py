"""Tests for rozkoduj_mcp.tools.fundamentals."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.fundamentals import fundamentals


def _mock_result() -> dict:
    return {
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "valuation": {"pe_ttm": 33.2, "pb": 52.1},
        "quality": {"piotroski": 9.0, "altman_z": 10.64},
        "analyst": {"buy": 23, "hold": 15, "sell": 2, "target_avg": 297.97},
        "earnings": {"next_date": "2026-04-24", "eps_forecast": 1.63},
        "dividends": {"yield": 0.004, "payout_ratio": 0.15},
    }


class TestFundamentals:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.fundamentals.scanner")
    async def test_returns_data(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.fundamentals = AsyncMock(return_value=_mock_result())

        result = await fundamentals("AAPL")

        mock_scanner.fundamentals.assert_called_once_with("AAPL")
        assert result["sector"] == "Technology"
        assert result["quality"]["piotroski"] == 9.0

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.fundamentals.scanner")
    async def test_has_all_sections(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.fundamentals = AsyncMock(return_value=_mock_result())

        result = await fundamentals("AAPL")

        assert set(result) >= {"valuation", "quality", "analyst", "earnings", "dividends"}
