"""Tests for rozkoduj_mcp.tools.digest."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.digest import digest


def _mock_digest_result(n_gems: int = 3) -> dict[str, Any]:
    return {
        "scope": "global",
        "screeners_queried": 15,
        "total_scanned": 1500,
        "gems_found": n_gems,
        "gems": [
            {
                "symbol": f"SYM{i}",
                "screener": "america",
                "close": 100.0 + i,
                "change_pct": -5.0 + i,
                "tags": ["VOLUME_SPIKE_3.0x", "BIG_MOVE_-5.0%"],
                "surprise_score": 5 - i,
            }
            for i in range(n_gems)
        ],
        "pulse": {"verdict": "RISK-OFF"},
    }


class TestDigest:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.digest.scanner")
    async def test_default_global(self, mock_scanner: MagicMock) -> None:
        mock_scanner.digest = AsyncMock(return_value=_mock_digest_result())

        result = await digest()

        mock_scanner.digest.assert_called_once_with(market=None, limit=20)
        assert result["scope"] == "global"
        assert len(result["gems"]) == 3

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.digest.scanner")
    async def test_with_market_filter(self, mock_scanner: MagicMock) -> None:
        mock_scanner.digest = AsyncMock(return_value=_mock_digest_result(1))

        result = await digest(market="poland")

        mock_scanner.digest.assert_called_once_with(market="poland", limit=20)
        assert len(result["gems"]) == 1

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.digest.scanner")
    async def test_limit_capped_at_100(self, mock_scanner: MagicMock) -> None:
        mock_scanner.digest = AsyncMock(return_value=_mock_digest_result())

        await digest(limit=200)

        call_kwargs = mock_scanner.digest.call_args[1]
        assert call_kwargs["limit"] == 100

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.digest.scanner")
    async def test_limit_minimum_1(self, mock_scanner: MagicMock) -> None:
        mock_scanner.digest = AsyncMock(return_value=_mock_digest_result())

        await digest(limit=0)

        call_kwargs = mock_scanner.digest.call_args[1]
        assert call_kwargs["limit"] == 1

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.digest.scanner")
    async def test_includes_pulse(self, mock_scanner: MagicMock) -> None:
        mock_scanner.digest = AsyncMock(return_value=_mock_digest_result())

        result = await digest()

        assert "pulse" in result
        assert result["pulse"]["verdict"] == "RISK-OFF"
