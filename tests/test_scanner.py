"""Tests for rozkoduj_mcp.services.scanner (API client)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rozkoduj_mcp.services.scanner import (
    _get_client,
    analyze,
    buzz,
    calendar,
    fundamentals,
    market_pulse,
    movers,
    scan_market,
    score,
)


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
        mock_client.post = AsyncMock(
            return_value=_mock_response(
                {"as_of": "2026-04-04T12:00:00", "results": [{"name": "BTC"}]}
            )
        )

        result = await scan_market(market="crypto", sort_by="volume", limit=10)

        assert len(result) == 1
        payload = mock_client.post.call_args[1]["json"]
        assert payload["market"] == "crypto"
        assert payload["limit"] == 10

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_scan_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"as_of": "2026-04-04", "results": []})
        )

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


class TestScore:
    """Tests for score()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_symbol_and_interval(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"symbol": "AAPL", "score": 78.0, "label": "BUY"})
        )

        result = await score(symbol="AAPL", interval="1d")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["symbol"] == "AAPL"
        assert payload["interval"] == "1d"
        assert result["score"] == 78.0

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_score_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response({"score": 50.0}))

        await score(symbol="BTCUSDT")

        url = mock_client.post.call_args[0][0]
        assert "/score" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data API error"):
            await score(symbol="AAPL")


class TestFundamentals:
    """Tests for fundamentals()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_symbol(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"symbol": "AAPL", "sector": "Technology"})
        )

        result = await fundamentals(symbol="AAPL")

        payload = mock_client.post.call_args[1]["json"]
        assert payload["symbol"] == "AAPL"
        assert result["sector"] == "Technology"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_fundamentals_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=_mock_response({"symbol": "AAPL"}))

        await fundamentals(symbol="AAPL")

        url = mock_client.post.call_args[0][0]
        assert "/fundamentals" in url


class TestBuzz:
    """Tests for buzz()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"query": "JSW", "attention": "HIGH"})
        )

        result = await buzz(query="JSW akcje", lang="pl", wiki_article="JSW_SA")

        params = mock_client.get.call_args[1]["params"]
        assert params["query"] == "JSW akcje"
        assert params["lang"] == "pl"
        assert result["attention"] == "HIGH"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_buzz_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"attention": "LOW"}))

        await buzz(query="AAPL stock")

        url = mock_client.get.call_args[0][0]
        assert "/buzz" in url


class TestMarketPulse:
    """Tests for market_pulse()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_market_pulse_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"verdict": "RISK-OFF", "vix": 24.5})
        )

        result = await market_pulse()

        url = mock_client.get.call_args[0][0]
        assert "/market-pulse" in url
        assert result["verdict"] == "RISK-OFF"


class TestCalendar:
    """Tests for calendar()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"count": 0, "events": []}))

        await calendar(days=14, countries="US,EU", importance=1)

        params = mock_client.get.call_args[1]["params"]
        assert params["days"] == 14
        assert params["countries"] == "US,EU"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_calendar_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"events": []}))

        await calendar()

        url = mock_client.get.call_args[0][0]
        assert "/calendar" in url
