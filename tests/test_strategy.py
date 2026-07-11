"""Tests for rozkoduj_mcp.tools.strategy."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.strategy import strategy


def _mock_result() -> dict[str, Any]:
    return {
        "algorithm_uid": "01JABC",
        "slug": "ma-cross-ema",
        "name": {"en": "MA Cross EMA"},
        "description": {"en": "Trend following on EMA cross"},
        "family": "ma_cross",
        "variant": "ema",
        "version": "v1",
        "best_run": {
            "symbol": "AAPL.US",
            "cagr": 0.45,
            "max_drawdown": -0.18,
            "win_rate": 0.61,
            "num_trades": 142,
            "rozkoduj_score": 78.0,
            "rozkoduj_band": "strong",
            "score_provisional": False,
            "risk_character": "balanced",
            "character_score": 64.0,
            "sparkline": [1.0, 1.1, 1.05, 1.22],
            "params_public": {"fast": 10, "slow": 30},
            "data_start": "2018-01-01",
            "data_end": "2026-04-01",
        },
        "created_at": "2026-04-01T00:00:00+00:00",
        "updated_at": "2026-04-01T00:00:00+00:00",
    }


class TestStrategy:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.strategy.scanner")
    async def test_returns_dossier(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.strategy_details = AsyncMock(return_value=_mock_result())

        result = await strategy("ma-cross-ema")

        mock_scanner.strategy_details.assert_called_once_with("ma-cross-ema")
        assert result["slug"] == "ma-cross-ema"
        assert result["best_run"]["cagr"] == 0.45
        assert result["best_run"]["rozkoduj_score"] == 78.0
        assert result["best_run"]["risk_character"] == "balanced"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.strategy.scanner")
    async def test_supports_algorithm_uid(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.strategy_details = AsyncMock(return_value=_mock_result())

        await strategy("01JABC")

        mock_scanner.strategy_details.assert_called_once_with("01JABC")
