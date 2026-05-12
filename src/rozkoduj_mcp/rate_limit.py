"""Per-tier hourly rate limiting via a pluggable usage store.

Quota policy lives here; storage is delegated to a ``UsageStore`` so the
public package never names the backend it talks to. The hosted instance
wires ``HttpUsageStore`` pointing at the rozkoduj data API; self-hosters
get ``NoOpUsageStore`` by default and can ship their own implementation.

Identity comes from the same JWKSTokenVerifier the MCP transport relies
on - forged tokens fail FastMCP auth before any tool runs, so the
verified ``tier`` claim is safe to trust for quota selection.
"""

import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from rozkoduj_mcp.auth import JWKSTokenVerifier

logger = logging.getLogger(__name__)

# Per-hour ceilings. Conservative pre-launch numbers - bumpable without a
# schema change on either side of the wire.
HOURLY_QUOTAS: dict[str, int] = {
    "anon": 20,
    "free": 120,
    "premium": 1200,
    "pro": 1200,
}

WINDOW_SECONDS = 3600

# Discovery endpoints are public by spec and must not require auth or
# burn quota (clients probe them before they have a token).
_SKIP_PATHS: frozenset[str] = frozenset({"/robots.txt", "/health", "/.well-known/mcp.json"})


class UsageStore(Protocol):
    """Pluggable rate-limit + audit backend.

    Implementations decide where rows live. Both methods fail open - the
    middleware treats backend errors as "no data, let the request through"
    so a transient backend blip never wedges live traffic.
    """

    async def count_recent(self, *, user_id: str | None, ip: str, since_iso: str) -> int: ...

    async def log(
        self,
        *,
        user_id: str | None,
        ip: str,
        tier: str,
        endpoint: str | None,
        status: str,
        duration_ms: int | None,
    ) -> None: ...

    async def aclose(self) -> None: ...


class NoOpUsageStore:
    """Default store for self-hosters - no counting, no logging.

    Returns 0 from ``count_recent`` so the middleware never blocks, and
    discards ``log`` calls. Self-hosters who want real quota enforcement
    plug in their own ``UsageStore`` implementation (Redis, Postgres,
    Memcached - whatever fits their stack).
    """

    async def count_recent(self, *, user_id: str | None, ip: str, since_iso: str) -> int:
        return 0

    async def log(
        self,
        *,
        user_id: str | None,
        ip: str,
        tier: str,
        endpoint: str | None,
        status: str,
        duration_ms: int | None,
    ) -> None:
        return None

    async def aclose(self) -> None:
        return None


class HttpUsageStore:
    """Forwards quota checks + audit rows to the rozkoduj data API."""

    def __init__(self, *, base_url: str, internal_key: str, http_timeout: float = 5.0) -> None:
        self._check_url = f"{base_url.rstrip('/')}/usage/check"
        self._log_url = f"{base_url.rstrip('/')}/usage/log"
        self._headers = {"X-Internal-Key": internal_key, "Content-Type": "application/json"}
        self._client = httpx.AsyncClient(timeout=http_timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def count_recent(self, *, user_id: str | None, ip: str, since_iso: str) -> int:
        try:
            resp = await self._client.post(
                self._check_url,
                json={"user_id": user_id, "ip": ip, "since_iso": since_iso},
                headers=self._headers,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("usage_check_failed: %s", exc)
            return 0
        body: dict[str, Any] = resp.json()
        return int(body.get("count", 0))

    async def log(
        self,
        *,
        user_id: str | None,
        ip: str,
        tier: str,
        endpoint: str | None,
        status: str,
        duration_ms: int | None,
    ) -> None:
        try:
            resp = await self._client.post(
                self._log_url,
                json={
                    "user_id": user_id,
                    "ip": ip,
                    "tier": tier,
                    "endpoint": endpoint,
                    "status": status,
                    "duration_ms": duration_ms,
                },
                headers=self._headers,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("usage_log_failed: %s", exc)


def _extract_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _iso_since(seconds: int) -> str:
    return (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Tier-aware hourly cap. Anon keyed by IP, authed by JWT sub."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        store: UsageStore,
        verifier: JWKSTokenVerifier,
    ) -> None:
        super().__init__(app)
        self._store = store
        self._verifier = verifier

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.url.path in _SKIP_PATHS:
            resp: Response = await call_next(request)
            return resp

        ip = _extract_ip(request)
        user_id, tier = await self._identify(request)
        cap = HOURLY_QUOTAS.get(tier, HOURLY_QUOTAS["anon"])
        count = await self._store.count_recent(
            user_id=user_id, ip=ip, since_iso=_iso_since(WINDOW_SECONDS)
        )

        if count >= cap:
            await self._store.log(
                user_id=user_id,
                ip=ip,
                tier=tier,
                endpoint=None,
                status="rate_limited",
                duration_ms=0,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "tier": tier,
                    "limit_per_hour": cap,
                    "retry_after_seconds": WINDOW_SECONDS,
                },
                headers={"Retry-After": str(WINDOW_SECONDS)},
            )

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        status_label = "success" if response.status_code < 400 else "error"
        await self._store.log(
            user_id=user_id,
            ip=ip,
            tier=tier,
            endpoint=None,
            status=status_label,
            duration_ms=duration_ms,
        )
        return response

    async def _identify(self, request: Request) -> tuple[str | None, str]:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return None, "anon"
        token = auth[7:]
        access_token = await self._verifier.verify_token(token)
        if access_token is None:
            return None, "anon"
        try:
            payload: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:  # pragma: no cover - verify_token already cleared sig + structure
            return access_token.client_id or None, "free"
        sub = payload.get("sub")
        user_id = str(sub) if sub else (access_token.client_id or None)
        tier = str(payload.get("tier", "free"))
        return user_id, tier


def default_store() -> UsageStore | None:
    """Build the usage store from environment, or ``None`` when unconfigured.

    Returns ``HttpUsageStore`` when both ``ROZKODUJ_API_URL`` and
    ``INTERNAL_API_KEY`` are set (hosted deployment). Returns ``None``
    otherwise so local dev, unit tests, and self-hosters keep running
    without the middleware attached. Self-hosters who want rate limits
    can wire their own ``UsageStore`` implementation directly.
    """
    internal_key = os.environ.get("INTERNAL_API_KEY")
    if not internal_key:
        return None
    base_url = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")
    return HttpUsageStore(base_url=base_url, internal_key=internal_key)
