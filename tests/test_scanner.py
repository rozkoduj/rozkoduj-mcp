"""Tests for rozkoduj_mcp.services.scanner (API client)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rozkoduj_mcp.services.scanner import _get_client, analyze, movers, scan_market


class TestGetClient:
    """Tests for _get_client()."""

    def test_raises_when_not_initialized(self) -> None:
        with pytest.raises(RuntimeError, match="not initialized"):
            _get_client()


def _mock_response(data: Any, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.is_success = status < 400
    return resp


class TestScanMarket:
    """Tests for scan_market()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_payload(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response([{"name": "BTC"}]))

        result = await scan_market(market="crypto", sort_by="volume", limit=10)

        assert len(result) == 1
        payload = mock_client.post.call_args[1]["json"]
        assert payload["market"] == "crypto"
        assert payload["limit"] == 10

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_scan_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response([]))

        await scan_market(market="america")

        url = mock_client.post.call_args[0][0]
        assert "/scan" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data API error"):
            await scan_market(market="crypto")


class TestAnalyze:
    """Tests for analyze()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_symbol_and_interval(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"summary": {}, "indicators": {}})
        )

        await analyze(symbol="BTCUSDT", interval="4h")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["symbol"] == "BTCUSDT"
        assert payload["interval"] == "4h"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_analyze_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response({"summary": {}}))

        await analyze(symbol="AAPL")

        url = mock_client.post.call_args[0][0]
        assert "/analyze" in url


class TestMovers:
    """Tests for movers()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_direction(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"market": "crypto", "gainers": []})
        )

        result = await movers(market="crypto", direction="gainers", limit=5)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["direction"] == "gainers"
        assert payload["limit"] == 5
        assert result["market"] == "crypto"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_movers_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response({"market": "crypto"}))

        await movers()

        url = mock_client.post.call_args[0][0]
        assert "/movers" in url
