"""Tests for rozkoduj_mcp.rate_limit (pluggable usage store + middleware)."""

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
    HttpUsageStore,
    NoOpUsageStore,
    RateLimitMiddleware,
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
        store = _stub_store(count=0)
        verifier = _stub_verifier(None)
        resp = TestClient(_build_app(store=store, verifier=verifier)).post(
            "/mcp", headers={"Authorization": "Bearer forged.jwt"}
        )
        assert resp.status_code == 200
        kwargs = store.count_recent.await_args.kwargs
        assert kwargs["user_id"] is None

    def test_valid_token_uses_jwt_sub_and_tier(self) -> None:
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


class TestNoOpUsageStore:
    @pytest.mark.anyio
    async def test_count_returns_zero(self) -> None:
        store = NoOpUsageStore()
        count = await store.count_recent(user_id=None, ip="x", since_iso="x")
        assert count == 0

    @pytest.mark.anyio
    async def test_log_is_noop(self) -> None:
        store = NoOpUsageStore()
        result = await store.log(
            user_id=None, ip="x", tier="anon", endpoint=None, status="success", duration_ms=0
        )
        assert result is None
        await store.aclose()


class TestHttpUsageStore:
    @pytest.mark.anyio
    async def test_check_posts_payload_with_internal_key(self) -> None:
        store = HttpUsageStore(base_url="https://api.example/", internal_key="secret")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"count": 42})
        store._client.post = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            count = await store.count_recent(
                user_id="u1", ip="1.2.3.4", since_iso="2026-05-12T00:00:00+00:00"
            )
            assert count == 42
            args, kwargs = store._client.post.await_args
            assert args[0] == "https://api.example/usage/check"
            assert kwargs["headers"]["X-Internal-Key"] == "secret"
            assert kwargs["json"]["user_id"] == "u1"
            assert kwargs["json"]["ip"] == "1.2.3.4"
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_check_fails_open_on_http_error(self) -> None:
        import httpx

        store = HttpUsageStore(base_url="https://api.example", internal_key="secret")
        store._client.post = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.ConnectError("down")
        )
        try:
            count = await store.count_recent(user_id=None, ip="x", since_iso="x")
            assert count == 0
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_check_missing_count_field_returns_zero(self) -> None:
        store = HttpUsageStore(base_url="https://api.example", internal_key="secret")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={})
        store._client.post = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            count = await store.count_recent(user_id=None, ip="x", since_iso="x")
            assert count == 0
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_log_posts_full_row(self) -> None:
        store = HttpUsageStore(base_url="https://api.example", internal_key="secret")
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        store._client.post = AsyncMock(return_value=mock_resp)  # type: ignore[method-assign]
        try:
            await store.log(
                user_id="u1",
                ip="1.2.3.4",
                tier="premium",
                endpoint="scan",
                status="success",
                duration_ms=42,
            )
            args, kwargs = store._client.post.await_args
            assert args[0] == "https://api.example/usage/log"
            row = kwargs["json"]
            assert row["user_id"] == "u1"
            assert row["tier"] == "premium"
            assert row["endpoint"] == "scan"
            assert row["duration_ms"] == 42
        finally:
            await store.aclose()

    @pytest.mark.anyio
    async def test_log_swallows_http_error(self) -> None:
        import httpx

        store = HttpUsageStore(base_url="https://api.example", internal_key="secret")
        store._client.post = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.ConnectError("down")
        )
        try:
            await store.log(
                user_id=None, ip="x", tier="anon", endpoint=None, status="error", duration_ms=0
            )
        finally:
            await store.aclose()


class TestDefaultStore:
    def test_returns_none_when_internal_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from rozkoduj_mcp.rate_limit import default_store

        monkeypatch.delenv("INTERNAL_API_KEY", raising=False)
        assert default_store() is None

    def test_builds_http_store_when_internal_key_present(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from rozkoduj_mcp.rate_limit import default_store

        monkeypatch.setenv("INTERNAL_API_KEY", "secret")
        monkeypatch.setenv("ROZKODUJ_API_URL", "https://api.example")
        store = default_store()
        assert isinstance(store, HttpUsageStore)


@pytest.fixture
def anyio_backend() -> Iterator[str]:
    yield "asyncio"
