"""Tests for rozkoduj_mcp.tools.movers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rozkoduj_mcp.tools.movers import movers


class TestMovers:
    """Tests for the movers MCP tool."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.movers.scanner")
    async def test_gainers(self, mock_scanner: MagicMock) -> None:
        mock_scanner.movers = AsyncMock(
            return_value={"market": "crypto", "gainers": [{"name": "BTC"}]}
        )

        result = await movers(direction="gainers")

        mock_scanner.movers.assert_called_once_with(
            market="crypto", direction="gainers", limit=10
        )
        assert "gainers" in result

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.movers.scanner")
    async def test_losers(self, mock_scanner: MagicMock) -> None:
        mock_scanner.movers = AsyncMock(
            return_value={"market": "crypto", "losers": [{"name": "ETH"}]}
        )

        result = await movers(direction="losers")

        mock_scanner.movers.assert_called_once_with(
            market="crypto", direction="losers", limit=10
        )
        assert "losers" in result
