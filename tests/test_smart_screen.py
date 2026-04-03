"""Tests for rozkoduj_mcp.tools.smart_screen."""

from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.smart_screen import smart_screen


class TestSmartScreen:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_unusual_volume(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[{"name": "NVDA", "close": 900}])

        result = await smart_screen("unusual_volume")

        assert len(result) == 1
        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["market"] == "america"
        assert any(f["left"] == "relative_volume_10d_calc" for f in call_kwargs["filters"])

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_oversold_bounce(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        result = await smart_screen("oversold_bounce", market="crypto")

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["market"] == "crypto"
        assert any(f["left"] == "RSI" for f in call_kwargs["filters"])
        assert result == []

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_all_presets_valid(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        for preset in ("unusual_volume", "oversold_bounce", "breakout", "momentum", "dividend"):
            await smart_screen(preset)  # type: ignore[arg-type]

        assert mock_scanner.scan_market.call_count == 5

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_clamps_limit(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await smart_screen("momentum", limit=999)

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["limit"] == 50
