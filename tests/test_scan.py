"""Tests for rozkoduj_mcp.tools.scan."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.scan import scan


def _mock_screen_result() -> list[dict[str, Any]]:
    return [
        {"name": "BTCUSDT", "close": 65000.0, "volume": 1_000_000, "change": 2.5},
        {"name": "ETHUSDT", "close": 3200.0, "volume": 800_000, "change": 1.8},
    ]


class TestScan:
    """Tests for the scan MCP tool."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.scan.scanner")
    async def test_basic_screen(self, mock_scanner: MagicMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=_mock_screen_result())

        result = await scan()

        mock_scanner.scan_market.assert_called_once_with(
            market="crypto",
            filters=None,
            columns=None,
            sort_by="volume",
            order="desc",
            limit=20,
        )
        assert len(result) == 2
        assert result[0]["name"] == "BTCUSDT"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.scan.scanner")
    async def test_with_filters(self, mock_scanner: MagicMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=_mock_screen_result())
        filters: list[dict[str, Any]] = [
            {"left": "volume", "operation": "greater", "right": 500_000}
        ]

        result = await scan(market="us", filters=filters, sort_by="change", order="asc")

        mock_scanner.scan_market.assert_called_once_with(
            market="us",
            filters=filters,
            columns=None,
            sort_by="change",
            order="asc",
            limit=20,
        )
        assert len(result) == 2

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.scan.scanner")
    async def test_limit_capped_at_100(self, mock_scanner: MagicMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await scan(limit=200)

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["limit"] == 100

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.scan.scanner")
    async def test_limit_minimum_1(self, mock_scanner: MagicMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await scan(limit=0)

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["limit"] == 1

    @pytest.mark.anyio
    async def test_rejects_too_many_filters(self) -> None:
        filters = [{"left": "volume", "operation": "greater", "right": i} for i in range(21)]
        with pytest.raises(ValueError, match="filters"):
            await scan(filters=filters)

    @pytest.mark.anyio
    async def test_rejects_too_many_columns(self) -> None:
        cols = [f"col_{i}" for i in range(51)]
        with pytest.raises(ValueError, match="columns"):
            await scan(columns=cols)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.scan.scanner")
    async def test_custom_columns(self, mock_scanner: MagicMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[{"name": "BTCUSDT", "RSI": 42.0}])

        result = await scan(columns=["name", "RSI"])

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["columns"] == ["name", "RSI"]
        assert result[0]["RSI"] == 42.0
