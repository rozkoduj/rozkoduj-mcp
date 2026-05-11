"""Tests for rozkoduj_mcp.rate_limit (Supabase-backed hourly quota)."""

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from rozkoduj_mcp.rate_limit import (
    HOURLY_QUOTAS,
    WINDOW_SECONDS,
    RateLimitMiddleware,
    SupabaseUsageStore,
    _extract_ip,
)


def _stub_verifier(access_token: object | None = None) -> MagicMock:
    """Mock JWKSTokenVerifier - returns the given AccessToken (or None)."""
    verifier = MagicMock()
    verifier.verify_token = AsyncMock(return_value=access_token)
    return verifier


def _stub_store(count: int = 0) -> MagicMock:
    store = MagicMock()
    store.count_recent = AsyncMock(return_value=count)
    store.log = AsyncMock(return_value=None)
    return store


def _build_app(*, store: MagicMock, verifier: MagicMock) -> Starlette:
    async def hello(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    return Starlette(
        routes=[Route("/mcp", hello, methods=["POST"])],
        middleware=[Middleware(RateLimitMiddleware, store=store, verifier=verifier)],
    )


class TestQuotas:
    def test_tier_ordering(self) -> None:
        """Free has more headroom than anon; premium more than free."""
        assert HOURLY_QUOTAS["anon"] < HOURLY_QUOTAS["free"]
        assert HOURLY_QUOTAS["free"] < HOURLY_QUOTAS["premium"]
        assert HOURLY_QUOTAS["pro"] >= HOURLY_QUOTAS["premium"]

    def test_window_is_one_hour(self) -> None:
        assert WINDOW_SECONDS == 3600


class TestAnonymous:
    def test_no_bearer_uses_anon_quota(self) -> None:
        store = _stub_store(count=0)
        verifier = _stub_verifier(None)
        resp = TestClient(_build_app(store=store, verifier=verifier)).post("/mcp")
        assert resp.status_code == 200
        store.count_recent.assert_awaited_once()
        kwargs = store.count_recent.await_args.kwargs
        assert kwargs["user_id"] is None
        # IP comes from the test client when no XFF header is set
        assert kwargs["ip"]

    def test_anon_at_cap_returns_429(self) -> None:
        store = _stub_store(count=HOURLY_QUOTAS["anon"])
        verifier = _stub_verifier(None)
        resp = TestClient(_build_app(store=store, verifier=verifier)).post("/mcp")
        assert resp.status_code == 429
        body = resp.json()
        assert body["tier"] == "anon"
        assert body["limit_per_hour"] == HOURLY_QUOTAS["anon"]
        assert resp.headers["Retry-After"] == str(WINDOW_SECONDS)


class TestAuthenticated:
    def test_invalid_token_falls_back_to_anon(self) -> None:
        """Forged/expired tokens are indistinguishable from anonymous."""
        store = _stub_store(count=0)
        verifier = _stub_verifier(None)
        resp = TestClient(_build_app(store=store, verifier=verifier)).post(
            "/mcp", headers={"Authorization": "Bearer forged.jwt"}
        )
        assert resp.status_code == 200
        # No user_id, no premium tier - identical to anonymous path
        kwargs = store.count_recent.await_args.kwargs
        assert kwargs["user_id"] is None

    def test_valid_token_uses_jwt_sub_and_tier(self) -> None:
        """Valid bearer -> verifier returns AccessToken -> middleware reads
        sub + tier off the JWT payload (no-verify decode is safe because
        the verifier already cleared sig/iss/aud/exp upstream).
        """
        import jwt as pyjwt
        from mcp.server.auth.provider import AccessToken

        token = pyjwt.encode({"sub": "user_abc", "tier": "premium"}, "dummy", algorithm="HS256")
        access = AccessToken(token=token, client_id="cli", scopes=["mcp:read"])
        store = _stub_store(count=0)
        verifier = _stub_verifier(access)
        resp = TestClient(_build_app(store=store, verifier=verifier)).post(
            "/mcp", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        kwargs = store.count_recent.await_args.kwargs
        assert kwargs["user_id"] == "user_abc"
        # Tier flows into the log row.
        log_kwargs = store.log.await_args.kwargs
        assert log_kwargs["tier"] == "premium"


class TestSkipPaths:
    def test_robots_skips_middleware(self) -> None:
        store = _stub_store(count=999)
        verifier = _stub_verifier(None)

        async def robots(request: Request) -> JSONResponse:
            return JSONResponse({"ok": True})

        app = Starlette(
            routes=[Route("/robots.txt", robots)],
            middleware=[Middleware(RateLimitMiddleware, store=store, verifier=verifier)],
        )
        resp = TestClient(app).get("/robots.txt")
        assert resp.status_code == 200
        store.count_recent.assert_not_called()
        store.log.assert_not_called()


class TestUsageLogged:
    def test_success_logs_status_success(self) -> None:
        store = _stub_store(count=0)
        verifier = _stub_verifier(None)
        TestClient(_build_app(store=store, verifier=verifier)).post("/mcp")
        store.log.assert_awaited_once()
        assert store.log.await_args.kwargs["status"] == "success"

    def test_rate_limited_logs_status_rate_limited(self) -> None:
        store = _stub_store(count=HOURLY_QUOTAS["anon"])
        verifier = _stub_verifier(None)
        TestClient(_build_app(store=store, verifier=verifier)).post("/mcp")
        store.log.assert_awaited_once()
        assert store.log.await_args.kwargs["status"] == "rate_limited"


class TestExtractIp:
    def test_uses_x_forwarded_for_first(self) -> None:
        request = MagicMock()
        request.headers = {"x-forwarded-for": "10.0.0.1, 192.168.1.1"}
        assert _extract_ip(request) == "10.0.0.1"

    def test_falls_back_to_client_host(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        assert _extract_ip(request) == "127.0.0.1"

    def test_returns_unknown_when_no_client(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _extract_ip(request) == "unknown"


class TestSupabaseUsageStoreCounting:
    @pytest.mark.anyio
    async def test_parses_postgrest_content_range(self) -> None:
        store = SupabaseUsageStore(url="https://test.supabase.co", key="test")
        mock_resp = MagicMock()
        mock_resp.headers = {"content-range": "0-99/247"}
        mock_resp.raise_for_status = MagicMock()
        store._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            count = await store.count_recent(
                user_id=None, ip="1.2.3.4", since_iso="2026-01-01T00:00:00+00:00"
            )
            assert count == 247
            # Anonymous path: query must filter user_id IS NULL plus ip = X
            params = store._client.get.await_args.kwargs["params"]
            assert params["ip"] == "eq.1.2.3.4"
            assert params["user_id"] == "is.null"
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_authed_query_filters_by_user_id(self) -> None:
        store = SupabaseUsageStore(url="https://test.supabase.co", key="test")
        mock_resp = MagicMock()
        mock_resp.headers = {"content-range": "0-0/5"}
        mock_resp.raise_for_status = MagicMock()
        store._client.get = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            await store.count_recent(
                user_id="user_xyz", ip="1.2.3.4", since_iso="2026-01-01T00:00:00+00:00"
            )
            params = store._client.get.await_args.kwargs["params"]
            assert params["user_id"] == "eq.user_xyz"
            assert "ip" not in params
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_fails_open_on_http_error(self) -> None:
        import httpx

        store = SupabaseUsageStore(url="https://test.supabase.co", key="test")
        store._client.get = AsyncMock(side_effect=httpx.ConnectError("down"))  # type: ignore[method-assign]
        try:
            count = await store.count_recent(
                user_id=None, ip="1.2.3.4", since_iso="2026-01-01T00:00:00+00:00"
            )
            assert count == 0
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_log_posts_to_service_usage(self) -> None:
        store = SupabaseUsageStore(url="https://test.supabase.co", key="test")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        store._client.post = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            await store.log(
                user_id=None,
                ip="1.2.3.4",
                tier="anon",
                endpoint=None,
                status="success",
                duration_ms=42,
            )
            store._client.post.assert_awaited_once()
            assert "/service_usage" in store._client.post.await_args.args[0]
            row = store._client.post.await_args.kwargs["json"]
            assert row["service"] == "mcp"
            assert row["tier"] == "anon"
            assert row["status"] == "success"
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_log_swallows_http_error(self) -> None:
        import httpx

        store = SupabaseUsageStore(url="https://test.supabase.co", key="test")
        store._client.post = AsyncMock(side_effect=httpx.ConnectError("down"))  # type: ignore[method-assign]
        try:
            # Must not raise - logging is best-effort.
            await store.log(
                user_id=None, ip="x", tier="anon", endpoint=None, status="error", duration_ms=0
            )
        finally:
            await store.aclose()


class TestDefaultStore:
    def test_returns_none_when_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from rozkoduj_mcp.rate_limit import default_store

        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
        assert default_store() is None

    def test_builds_store_when_env_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from rozkoduj_mcp.rate_limit import default_store

        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_SECRET_KEY", "secret")
        store = default_store()
        assert store is not None


@pytest.fixture
def anyio_backend() -> Iterator[str]:
    yield "asyncio"
