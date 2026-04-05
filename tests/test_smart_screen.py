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
        assert call_kwargs["market"] == "us"
        assert any(f["left"] == "relative_volume" for f in call_kwargs["filters"])

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

        presets = (
            "unusual_volume",
            "oversold_bounce",
            "breakout",
            "momentum",
            "dividend",
            "value",
            "growth",
        )
        for preset in presets:
            await smart_screen(preset)  # type: ignore[arg-type]

        assert mock_scanner.scan_market.call_count == len(presets)

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_value_preset_uses_fundamentals(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await smart_screen("value")

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert any(f["left"] == "pe_ttm" for f in call_kwargs["filters"])
        assert any(f["left"] == "piotroski" for f in call_kwargs["filters"])

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_growth_preset_uses_fundamentals(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await smart_screen("growth")

        call_kwargs = mock_scanner.scan_market.call_args[1]
        filter_fields = {f["left"] for f in call_kwargs["filters"]}
        assert "eps_growth_yoy" in filter_fields
        assert "EMA20" in filter_fields

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.smart_screen.scanner")
    async def test_clamps_limit(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.scan_market = AsyncMock(return_value=[])

        await smart_screen("momentum", limit=999)

        call_kwargs = mock_scanner.scan_market.call_args[1]
        assert call_kwargs["limit"] == 50
