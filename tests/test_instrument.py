"""Tests for rozkoduj_mcp.tools.instrument (dual-mode: catalog / dossier)."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp.tools.instrument import instrument


def _catalog_result() -> dict[str, Any]:
    return {
        "items": [
            {
                "instrument_id": "AAPL.US",
                "ticker": "AAPL",
                "display_name": "Apple Inc",
                "asset_class": "equity",
                "exchange_label": "NASDAQ",
                "currency": "USD",
                "sector": "Technology",
                "status": "live",
            }
        ],
        "total": 512,
        "limit": 50,
        "offset": 0,
    }


def _dossier_result() -> dict[str, Any]:
    return {
        "instrument_id": "AAPL.US",
        "ticker": "AAPL",
        "display_name": "Apple Inc",
        "asset_class": "equity",
        "exchange_label": "NASDAQ",
        "currency": "USD",
        "sector": "Technology",
        "status": "live",
        "last_close": 231.5,
        "stats": {
            "asof_date": "2026-07-10",
            "cagr": 0.21,
            "ann_vol": 0.28,
            "max_dd": -0.31,
            "time_underwater_pct": 42.0,
            "kaufman_er": 0.18,
            "trend_share": 0.55,
            "radar": [{"axis": "momentum", "value": 0.7}],
            "verdict": {"band": "strong"},
        },
    }


class TestCatalogMode:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.instrument.scanner")
    async def test_no_symbol_lists_the_catalog(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_instruments = AsyncMock(return_value=_catalog_result())

        result = await instrument()

        mock_scanner.list_instruments.assert_called_once_with(
            asset_class=None, status=None, limit=50, offset=0
        )
        mock_scanner.instrument_details.assert_not_called()
        assert result["total"] == 512

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.instrument.scanner")
    async def test_catalog_filters_forwarded(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.list_instruments = AsyncMock(return_value=_catalog_result())

        await instrument(asset_class="crypto", status="live", limit=10, offset=5)

        mock_scanner.list_instruments.assert_called_once_with(
            asset_class="crypto", status="live", limit=10, offset=5
        )


class TestDossierMode:
    @pytest.mark.anyio
    @patch("rozkoduj_mcp.tools.instrument.scanner")
    async def test_symbol_fetches_the_dossier(self, mock_scanner: AsyncMock) -> None:
        mock_scanner.instrument_details = AsyncMock(return_value=_dossier_result())

        result = await instrument(symbol="AAPL")

        mock_scanner.instrument_details.assert_called_once_with("AAPL")
        mock_scanner.list_instruments.assert_not_called()
        assert result["instrument_id"] == "AAPL.US"
        assert result["stats"]["cagr"] == 0.21
        assert result["stats"]["radar"][0]["axis"] == "momentum"
