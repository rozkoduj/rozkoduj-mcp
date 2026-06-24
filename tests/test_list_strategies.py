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
                "name": {"en": "MA Cross EMA"},
                "best_run": {
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


class TestListStrategies:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.list_strategies.scanner")
    async def test_returns_strategies(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_strategies = AsyncMock(return_value=_mock_result())

        result = await list_strategies()

        mock_scanner.list_strategies.assert_called_once_with(
            status="active",
            sort="score_desc",
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
            status="all", sort="apy_desc", family="ma_cross", limit=5, offset=10
        )

        mock_scanner.list_strategies.assert_called_once_with(
            status="all",
            sort="apy_desc",
            visibility="public",
            family="ma_cross",
            limit=5,
            offset=10,
        )
