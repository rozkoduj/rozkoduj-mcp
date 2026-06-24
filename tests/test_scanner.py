"""Tests for rozkoduj_mcp.services.scanner (API client)."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rozkoduj_mcp.services import scanner as scanner_mod
from rozkoduj_mcp.services.scanner import (
    _get_client,
    _get_semaphore,
    analyze,
    buzz,
    calendar,
    decode,
    digest,
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


class TestGetSemaphore:
    """Tests for _get_semaphore()."""

    def test_raises_when_not_initialized(self) -> None:
        # Bypass the autouse fixture for this one assertion.
        scanner_mod._request_semaphore = None
        with pytest.raises(RuntimeError, match="not initialized"):
            _get_semaphore()


def _mock_response(data: Any, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.is_success = status < 400
    return resp


def _mock_429_response(retry_after: str | None = "3600") -> MagicMock:
    """Mock httpx response that raises HTTPStatusError(429) on raise_for_status()."""
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": retry_after} if retry_after is not None else {}
    resp.is_success = False
    err = httpx.HTTPStatusError("429", request=MagicMock(), response=resp)
    resp.raise_for_status = MagicMock(side_effect=err)
    return resp


def _mock_status_error_response(status: int) -> MagicMock:
    """Mock httpx response that raises HTTPStatusError(<status>) on raise_for_status()."""
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {}
    resp.is_success = False
    err = httpx.HTTPStatusError(str(status), request=MagicMock(), response=resp)
    resp.raise_for_status = MagicMock(side_effect=err)
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

        await scan_market(market="us")

        url = mock_client.post.call_args[0][0]
        assert "/scan" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await scan_market(market="crypto")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_surfaces_rate_limit_with_retry_after(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_429_response("1800"))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*1800"):
            await scan_market(market="crypto")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_without_retry_after_falls_back(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_429_response(retry_after=None))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*later"):
            await scan_market(market="crypto")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_non_429_status_error_raises_generic(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_status_error_response(503))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
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

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await analyze(symbol="AAPL")


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
            return_value=_mock_response(
                {"symbol": "AAPL", "score": 78.0, "label": "BUY"}
            )
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

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
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

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await fundamentals(symbol="AAPL")


class TestBuzz:
    """Tests for buzz()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"query": "AAPL", "attention": "HIGH"})
        )

        result = await buzz(query="AAPL stock", lang="en", wiki_article="Apple_Inc")

        params = mock_client.get.call_args[1]["params"]
        assert params["query"] == "AAPL stock"
        assert params["lang"] == "en"
        assert result["attention"] == "HIGH"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_buzz_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"attention": "LOW"}))

        await buzz(query="AAPL stock")

        url = mock_client.get.call_args[0][0]
        assert "/buzz" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await buzz(query="AAPL")


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

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await market_pulse()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_surfaces_rate_limit_with_retry_after(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get = AsyncMock(return_value=_mock_429_response("900"))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*900"):
            await market_pulse()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_non_429_status_error_raises_generic(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get = AsyncMock(return_value=_mock_status_error_response(502))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await market_pulse()


class TestCalendar:
    """Tests for calendar()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"count": 0, "events": []})
        )

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

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await calendar()


class TestDigestScanner:
    """Tests for scanner.digest()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_default_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"gems": [], "scope": "global"})
        )

        result = await digest()

        params = mock_client.get.call_args[1]["params"]
        assert params["limit"] == 20
        assert "market" not in params
        assert result["scope"] == "global"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_with_market(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"gems": [], "scope": "crypto"})
        )

        result = await digest(market="crypto")

        params = mock_client.get.call_args[1]["params"]
        assert params["market"] == "crypto"
        assert result["scope"] == "crypto"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_digest_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"gems": []}))

        await digest()

        url = mock_client.get.call_args[0][0]
        assert "/digest" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await digest()


class TestDecodeScanner:
    """Tests for scanner.decode()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_default_params(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"symbol": "AAPL", "technical": {}})
        )

        result = await decode(symbol="AAPL")

        params = mock_client.get.call_args[1]["params"]
        assert params["symbol"] == "AAPL"
        assert "query" not in params
        assert "lang" not in params
        assert result["symbol"] == "AAPL"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_with_query(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"symbol": "SHL.DE"}))

        await decode(symbol="SHL.DE", query="Siemens Healthineers")

        params = mock_client.get.call_args[1]["params"]
        assert params["query"] == "Siemens Healthineers"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_with_non_en_lang(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"symbol": "ASML.AS"}))

        await decode(symbol="ASML.AS", lang="de")

        params = mock_client.get.call_args[1]["params"]
        assert params["lang"] == "de"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_en_lang_not_sent(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"symbol": "AAPL"}))

        await decode(symbol="AAPL", lang="en")

        params = mock_client.get.call_args[1]["params"]
        assert "lang" not in params

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_decode_endpoint(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(return_value=_mock_response({"symbol": "X"}))

        await decode(symbol="X")

        url = mock_client.get.call_args[0][0]
        assert "/decode" in url

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_api_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await decode(symbol="AAPL")


class TestListStrategies:
    """Tests for list_strategies()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import list_strategies

        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_strategies(
            status="active", sort="score_desc", visibility="public", limit=10, offset=0
        )

        params = mock_client.get.call_args[1]["params"]
        assert params["status"] == "active"
        assert params["sort"] == "score_desc"
        assert params["visibility"] == "public"
        assert params["limit"] == 10
        assert params["offset"] == 0
        assert "family" not in params

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_family_included_when_set(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import list_strategies

        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_strategies(family="ma_cross")

        params = mock_client.get.call_args[1]["params"]
        assert params["family"] == "ma_cross"


class TestStrategyDetails:
    """Tests for strategy_details()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_calls_correct_path(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import strategy_details

        mock_client.get = AsyncMock(
            return_value=_mock_response({"slug": "ma-cross-ema"})
        )

        await strategy_details("ma-cross-ema")

        url = mock_client.get.call_args[0][0]
        assert url == "/strategies/ma-cross-ema"


class TestSearchArticles:
    """Tests for search_articles()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_payload(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import search_articles

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        await search_articles(query="momentum", locale="en", limit=3)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["query"] == "momentum"
        assert payload["locale"] == "en"
        assert payload["limit"] == 3

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_locale_omitted_when_none(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import search_articles

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        await search_articles(query="q")

        payload = mock_client.post.call_args[1]["json"]
        assert "locale" not in payload


class TestSearchKnowledge:
    """Tests for search_knowledge() outbound auth header behaviour."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_uses_iam_token_and_user_identity_headers(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.auth import (
            current_user_id,
            current_user_scopes,
            current_user_tier,
        )
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        user_reset = current_user_id.set("user-42")
        tier_reset = current_user_tier.set("pro")
        scopes_reset = current_user_scopes.set("mcp:read mcp:knowledge:read")
        try:
            with patch.object(
                iam_client, "_fetch", new=AsyncMock(return_value="iam-token-xyz")
            ):
                iam_client.reset_cache()
                await search_knowledge(query="x", limit=1)
        finally:
            current_user_scopes.reset(scopes_reset)
            current_user_tier.reset(tier_reset)
            current_user_id.reset(user_reset)
            iam_client.reset_cache()

        kwargs = mock_client.post.call_args[1]
        assert kwargs["json"] == {"query": "x", "limit": 1}
        headers = kwargs["headers"]
        assert headers["Authorization"] == "Bearer iam-token-xyz"
        assert headers["X-User-Id"] == "user-42"
        assert headers["X-User-Tier"] == "pro"
        assert headers["X-User-Scopes"] == "mcp:read mcp:knowledge:read"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_no_auth_when_nothing_available(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        with patch.dict("os.environ", {"ROZKODUJ_API_KEY": ""}):
            await search_knowledge(query="x")

        assert mock_client.post.call_args[1]["headers"] == {}

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_omits_tier_header_when_claim_absent(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.auth import current_user_id
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        user_reset = current_user_id.set("user-without-tier")
        try:
            with patch.object(
                iam_client, "_fetch", new=AsyncMock(return_value="iam-token-xyz")
            ):
                iam_client.reset_cache()
                await search_knowledge(query="x")
        finally:
            current_user_id.reset(user_reset)
            iam_client.reset_cache()

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-User-Id"] == "user-without-tier"
        assert "X-User-Tier" not in headers

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_forwards_client_ip_header(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp.auth import current_client_ip
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        ip_reset = current_client_ip.set("203.0.113.7")
        try:
            await search_knowledge(query="x")
        finally:
            current_client_ip.reset(ip_reset)

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Client-Ip"] == "203.0.113.7"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_omits_client_ip_header_when_unset(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        await search_knowledge(query="x")

        assert "X-Client-Ip" not in mock_client.post.call_args[1]["headers"]

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_forwards_trace_header_to_api(
        self,
        mock_client: AsyncMock,
    ) -> None:
        """Inbound Cloud Run trace header propagates so GCP Logging joins
        the MCP and API entries under the same trace_id.
        """
        from rozkoduj_mcp.logging import current_trace_header
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        token = current_trace_header.set("trace-abc/0;o=1")
        try:
            await search_knowledge(query="x")
        finally:
            current_trace_header.reset(token)

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Cloud-Trace-Context"] == "trace-abc/0;o=1"


class TestSelfHostApiKey:
    """Outbound auth falls back to ROZKODUJ_API_KEY when no IAM token is
    available (self-hosted deployments off Cloud Run)."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_falls_back_to_api_key_when_no_iam_token(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_" + "a" * 40}),
        ):
            iam_client.reset_cache()
            try:
                await search_knowledge(query="x")
            finally:
                iam_client.reset_cache()

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer " + "rzk_" + "a" * 40

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_iam_token_takes_precedence_over_api_key(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value="iam-token")),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_should_be_ignored"}),
        ):
            iam_client.reset_cache()
            try:
                await search_knowledge(query="x")
            finally:
                iam_client.reset_cache()

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer iam-token"


class TestPerTierForwarding:
    """The resolved tier is forwarded verbatim as X-User-Tier."""

    @pytest.mark.anyio
    @pytest.mark.parametrize("tier", ["free", "pro"])
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_forwards_user_tier(self, mock_client: AsyncMock, tier: str) -> None:
        from rozkoduj_mcp.auth import current_user_id, current_user_tier
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        uid = current_user_id.set("user-1")
        tok = current_user_tier.set(tier)
        try:
            await search_knowledge(query="x")
        finally:
            current_user_tier.reset(tok)
            current_user_id.reset(uid)

        assert mock_client.post.call_args[1]["headers"]["X-User-Tier"] == tier


_VALID_KEY = "rzk_" + "a" * 40  # rzk_ + 40 hex = 44 chars


class TestSelfHostCredential:
    def test_valid_key_accepted(self) -> None:
        from rozkoduj_mcp.services.scanner import _self_host_credential

        with patch.dict("os.environ", {"ROZKODUJ_API_KEY": _VALID_KEY}):
            assert _self_host_credential() == _VALID_KEY

    def test_malformed_key_rejected(self) -> None:
        from rozkoduj_mcp.services.scanner import _self_host_credential

        with patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_short"}):
            assert _self_host_credential() is None

    def test_absent_key_returns_none(self) -> None:
        from rozkoduj_mcp.services.scanner import _self_host_credential

        with patch.dict("os.environ", {}, clear=True):
            assert _self_host_credential() is None

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_malformed_key_sends_no_auth_header(
        self, mock_client: AsyncMock
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.services.scanner import search_knowledge

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "not-a-valid-key"}),
        ):
            iam_client.reset_cache()
            try:
                await search_knowledge(query="x")
            finally:
                iam_client.reset_cache()

        headers = mock_client.post.call_args[1]["headers"]
        assert "Authorization" not in headers
