"""Tests for rozkoduj_mcp.tools.list_strategies."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.list_strategies import list_strategies


def _mock_result() -> dict[str, Any]:
    return {
        "items": [
            {
                "algorithm_uid": "01JABC",
                "slug": "ma-cross-ema",
                "name": {"en": "MA Cross EMA", "pl": "Krzyż MA EMA"},
                "best_run": {"sharpe": 2.4, "cagr": 0.45},
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }


class TestListStrategies:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_returns_strategies(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        result = await list_strategies()

        mock_scanner.list_strategies.assert_called_once_with(
            status="active",
            sort="sharpe_desc",
            visibility="public",
            family=None,
            limit=20,
            offset=0,
        )
        assert result["total"] == 1
        assert result["items"][0]["slug"] == "ma-cross-ema"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_custom_filters(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await list_strategies(
            status="all", sort="cagr_desc", family="ma_cross", limit=5, offset=10
        )

        mock_scanner.list_strategies.assert_called_once_with(
            status="all",
            sort="cagr_desc",
            visibility="public",
            family="ma_cross",
            limit=5,
            offset=10,
        )

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_clamps_limit_high(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await list_strategies(limit=999)

        kwargs = mock_scanner.list_strategies.call_args.kwargs
        assert kwargs["limit"] == 50

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_clamps_limit_low(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await list_strategies(limit=0)

        kwargs = mock_scanner.list_strategies.call_args.kwargs
        assert kwargs["limit"] == 1

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_clamps_offset_negative(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await list_strategies(offset=-5)

        kwargs = mock_scanner.list_strategies.call_args.kwargs
        assert kwargs["offset"] == 0

    @pytest.mark.anyio
    async def test_rejects_long_family(self) -> None:
        with pytest.raises(ValueError, match="family"):
            await list_strategies(family="x" * 200)
