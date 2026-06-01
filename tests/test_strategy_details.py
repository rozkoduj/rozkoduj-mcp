"""Tests for rozkoduj_mcp.tools.strategy_details."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.strategy_details import strategy_details


def _mock_result() -> dict[str, Any]:
    return {
        "algorithm_uid": "01JABC",
        "slug": "ma-cross-ema",
        "name": {"en": "MA Cross EMA"},
        "description": {"en": "Trend following on EMA cross"},
        "family": "ma_cross",
        "variant": "ema",
        "version": "v1",
        "tags": ["trend"],
        "best_run": {"sharpe": 2.4, "cagr": 0.45, "max_drawdown": -0.18},
        "created_at": "2026-04-01T00:00:00+00:00",
        "updated_at": "2026-04-01T00:00:00+00:00",
    }


class TestStrategyDetails:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.strategy_details.scanner")
    async def test_returns_strategy(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.strategy_details = AsyncMock(return_value=_mock_result())

        result = await strategy_details("ma-cross-ema")

        mock_scanner.strategy_details.assert_called_once_with("ma-cross-ema")
        assert result["slug"] == "ma-cross-ema"
        assert result["best_run"]["sharpe"] == 2.4

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.strategy_details.scanner")
    async def test_supports_algorithm_uid(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.strategy_details = AsyncMock(return_value=_mock_result())

        await strategy_details("01JABC")

        mock_scanner.strategy_details.assert_called_once_with("01JABC")
