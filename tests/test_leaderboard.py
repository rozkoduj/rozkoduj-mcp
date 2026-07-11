"""Tests for rozkoduj_mcp.tools.leaderboard."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.leaderboard import leaderboard


def _mock_result() -> dict[str, Any]:
    return {
        "items": [
            {
                "algorithm_uid": "01JABC",
                "slug": "ma-cross-ema",
                "name": {"en": "MA Cross EMA"},
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
                },
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }


class TestLeaderboard:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.leaderboard.scanner")
    async def test_returns_ranked_strategies(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        result = await leaderboard()

        mock_scanner.list_strategies.assert_called_once_with(
            status="active",
            sort="score_desc",
            visibility="public",
            family=None,
            symbol=None,
            limit=20,
            offset=0,
        )
        assert result["total"] == 1
        assert result["items"][0]["slug"] == "ma-cross-ema"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.leaderboard.scanner")
    async def test_custom_filters(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await leaderboard(
            status="all", sort="apy_desc", family="ma_cross", limit=5, offset=10
        )

        mock_scanner.list_strategies.assert_called_once_with(
            status="all",
            sort="apy_desc",
            visibility="public",
            family="ma_cross",
            symbol=None,
            limit=5,
            offset=10,
        )

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.leaderboard.scanner")
    async def test_symbol_filter_forwarded(self, mock_scanner: AsyncMock) -> None:
        # "What strategy works best on AAPL?" - the symbol reaches the API.
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        await leaderboard(symbol="AAPL")

        assert mock_scanner.list_strategies.call_args.kwargs["symbol"] == "AAPL"
