"""Tests for rozkoduj_mcp.services.scanner (API client)."""

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rozkoduj_mcp.services import scanner as scanner_mod
from rozkoduj_mcp.services.scanner import (
    _get_client,
    _get_semaphore,
    list_strategies,
    search_research,
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


class TestPostErrorPaths:
    """The shared _post() error handling, exercised through search_research."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_connect_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await search_research(query="momentum")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_surfaces_rate_limit_with_retry_after(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_429_response("1800"))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*1800"):
            await search_research(query="momentum")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_without_retry_after_falls_back(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_429_response(retry_after=None))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*later"):
            await search_research(query="momentum")

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_non_429_status_error_raises_generic(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(return_value=_mock_status_error_response(503))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await search_research(query="momentum")


class TestGetErrorPaths:
    """The shared _get() error handling, exercised through list_strategies."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_connect_error_raises_runtime(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await list_strategies()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_429_surfaces_rate_limit_with_retry_after(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get = AsyncMock(return_value=_mock_429_response("900"))

        with pytest.raises(RuntimeError, match=r"Rate limit exceeded.*900"):
            await list_strategies()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_non_429_status_error_raises_generic(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.get = AsyncMock(return_value=_mock_status_error_response(502))

        with pytest.raises(RuntimeError, match="Data backend unavailable"):
            await list_strategies()

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_404_surfaces_not_found(self, mock_client: AsyncMock) -> None:
        # A 404 must read as "not found" (a bad slug), not as a backend outage.
        from rozkoduj_mcp.services.scanner import strategy_details

        mock_client.get = AsyncMock(return_value=_mock_status_error_response(404))

        with pytest.raises(RuntimeError, match="not found"):
            await strategy_details("nonexistent-slug")


class TestListStrategies:
    """Tests for list_strategies()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_params(self, mock_client: AsyncMock) -> None:
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
        assert "symbol" not in params

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_family_included_when_set(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_strategies(family="ma_cross")

        params = mock_client.get.call_args[1]["params"]
        assert params["family"] == "ma_cross"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_symbol_included_when_set(self, mock_client: AsyncMock) -> None:
        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_strategies(symbol="AAPL")

        params = mock_client.get.call_args[1]["params"]
        assert params["symbol"] == "AAPL"


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


class TestSearchResearch:
    """Tests for search_research()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_sends_payload_to_research_endpoint(
        self, mock_client: AsyncMock
    ) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "articles": [], "knowledge": []})
        )

        await search_research(query="momentum", locale="en", limit=3)

        url = mock_client.post.call_args[0][0]
        assert url == "/research/search"
        payload = mock_client.post.call_args[1]["json"]
        assert payload["query"] == "momentum"
        assert payload["locale"] == "en"
        assert payload["limit"] == 3

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_locale_omitted_when_none(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "articles": [], "knowledge": []})
        )

        await search_research(query="q")

        payload = mock_client.post.call_args[1]["json"]
        assert "locale" not in payload


class TestInstruments:
    """Tests for list_instruments() / instrument_details()."""

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_catalog_sends_only_set_filters(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import list_instruments

        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_instruments(asset_class="crypto", limit=10, offset=0)

        url = mock_client.get.call_args[0][0]
        params = mock_client.get.call_args[1]["params"]
        assert url == "/instruments"
        assert params["asset_class"] == "crypto"
        assert "status" not in params

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_catalog_status_filter(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import list_instruments

        mock_client.get = AsyncMock(
            return_value=_mock_response({"items": [], "total": 0})
        )

        await list_instruments(status="live")

        assert mock_client.get.call_args[1]["params"]["status"] == "live"

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_dossier_calls_symbol_path(self, mock_client: AsyncMock) -> None:
        from rozkoduj_mcp.services.scanner import instrument_details

        mock_client.get = AsyncMock(
            return_value=_mock_response({"instrument_id": "AAPL.US"})
        )

        await instrument_details("AAPL")

        assert mock_client.get.call_args[0][0] == "/instruments/AAPL"


class TestOutboundHeaders:
    """Outbound auth/identity header behaviour, exercised through search_research()."""

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
        from rozkoduj_mcp.services.scanner import search_research

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
                await search_research(query="x", limit=1)
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        with patch.dict("os.environ", {"ROZKODUJ_API_KEY": ""}):
            await search_research(query="x")

        assert mock_client.post.call_args[1]["headers"] == {}

    @pytest.mark.anyio
    @patch("rozkoduj_mcp.services.scanner.client")
    async def test_omits_tier_header_when_claim_absent(
        self,
        mock_client: AsyncMock,
    ) -> None:
        from rozkoduj_mcp import iam_client
        from rozkoduj_mcp.auth import current_user_id
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        user_reset = current_user_id.set("user-without-tier")
        try:
            with patch.object(
                iam_client, "_fetch", new=AsyncMock(return_value="iam-token-xyz")
            ):
                iam_client.reset_cache()
                await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        ip_reset = current_client_ip.set("203.0.113.7")
        try:
            await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        await search_research(query="x")

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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )

        token = current_trace_header.set("trace-abc/0;o=1")
        try:
            await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_" + "a" * 40}),
        ):
            iam_client.reset_cache()
            try:
                await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value="iam-token")),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_should_be_ignored"}),
        ):
            iam_client.reset_cache()
            try:
                await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        uid = current_user_id.set("user-1")
        tok = current_user_tier.set(tier)
        try:
            await search_research(query="x")
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
        from rozkoduj_mcp.services.scanner import search_research

        mock_client.post = AsyncMock(
            return_value=_mock_response({"query": "q", "items": []})
        )
        with (
            patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)),
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "not-a-valid-key"}),
        ):
            iam_client.reset_cache()
            try:
                await search_research(query="x")
            finally:
                iam_client.reset_cache()

        headers = mock_client.post.call_args[1]["headers"]
        assert "Authorization" not in headers


class TestLogSelfHostStatus:
    def test_logs_absent(self, caplog: pytest.LogCaptureFixture) -> None:
        from rozkoduj_mcp.services.scanner import log_self_host_status

        with patch.dict("os.environ", {}, clear=True), caplog.at_level(logging.INFO):
            log_self_host_status()
        assert "absent" in caplog.text

    def test_logs_configured_prefix_not_secret(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from rozkoduj_mcp.services.scanner import log_self_host_status

        key = "rzk_" + "b" * 40
        with (
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": key}),
            caplog.at_level(logging.INFO),
        ):
            log_self_host_status()
        assert "configured" in caplog.text
        assert key not in caplog.text  # secret never logged
        assert key[:12] in caplog.text  # 12-char prefix is fine

    def test_logs_malformed_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        from rozkoduj_mcp.services.scanner import log_self_host_status

        with (
            patch.dict("os.environ", {"ROZKODUJ_API_KEY": "rzk_bad"}),
            caplog.at_level(logging.WARNING),
        ):
            log_self_host_status()
        assert "malformed" in caplog.text
