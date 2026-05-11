"""Per-tier hourly rate limiting backed by Supabase service_usage.

Mirrors the rozkoduj-web chat_usage pattern - one row per request, quota
check = COUNT(rows in last hour) >= tier cap. Cold-start safe (Cloud Run
in-process state dies on every revision); cross-instance safe (single
source of truth for any number of replicas).

Tier identification uses the same JWKSTokenVerifier the MCP transport
relies on. Forged tokens fail FastMCP auth before any tool runs, so it
is safe to trust the verified `tier` claim for quota selection.

Falls open when SUPABASE_URL / SUPABASE_SECRET_KEY are not configured -
local dev and unit tests keep working without the ledger.
"""

import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from rozkoduj_mcp.auth import JWKSTokenVerifier

logger = logging.getLogger(__name__)

# Per-hour ceilings. Same proportions as the rozkoduj-web chat ledger
# (anon : logged ~= 1 : 6), extended with a premium tier for paying users.
# Conservative pre-launch numbers - bumpable without a schema change.
HOURLY_QUOTAS: dict[str, int] = {
    "anon": 20,
    "free": 120,
    "premium": 1200,
    "pro": 1200,
}

WINDOW_SECONDS = 3600
SERVICE = "mcp"

# Outer Starlette routes handle these without touching MCP - never count.
# Discovery endpoints are public by spec and must not require auth or
# burn quota (clients probe them before they have a token).
_SKIP_PATHS: frozenset[str] = frozenset({"/robots.txt", "/health", "/.well-known/mcp.json"})


class SupabaseUsageStore:
    """REST client for the service_usage table."""

    def __init__(self, *, url: str, key: str, http_timeout: float = 5.0) -> None:
        self._rest_url = f"{url}/rest/v1"
        self._headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(timeout=http_timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def count_recent(self, *, user_id: str | None, ip: str, since_iso: str) -> int:
        params: dict[str, str] = {
            "select": "id",
            "service": f"eq.{SERVICE}",
            "created_at": f"gte.{since_iso}",
        }
        if user_id:
            params["user_id"] = f"eq.{user_id}"
        else:
            params["ip"] = f"eq.{ip}"
            params["user_id"] = "is.null"
        try:
            resp = await self._client.get(
                f"{self._rest_url}/service_usage",
                params=params,
                headers={**self._headers, "Prefer": "count=exact"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("rate_limit_count_failed: %s", exc)
            return 0
        # PostgREST returns Content-Range: 0-N/total when Prefer: count=exact.
        # Fail-open on parse issues - blocking real traffic on a parse bug is worse.
        cr = resp.headers.get("content-range", "*/0")
        try:
            return int(cr.rsplit("/", 1)[-1])
        except ValueError:
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
        row = {
            "service": SERVICE,
            "user_id": user_id,
            "ip": ip,
            "tier": tier,
            "endpoint": endpoint,
            "status": status,
            "duration_ms": duration_ms,
        }
        try:
            resp = await self._client.post(
                f"{self._rest_url}/service_usage",
                json=row,
                headers=self._headers,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("rate_limit_log_failed: %s", exc)


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
        store: SupabaseUsageStore,
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
        # `verify_token` validates sig/iss/aud/exp but doesn't expose the
        # tier claim. The payload is already trustworthy at this point,
        # so a no-verify decode is safe to read the remaining claims.
        try:
            payload: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError:  # pragma: no cover - verify_token already cleared sig + structure
            return access_token.client_id or None, "free"
        sub = payload.get("sub")
        user_id = str(sub) if sub else (access_token.client_id or None)
        tier = str(payload.get("tier", "free"))
        return user_id, tier


def default_store() -> SupabaseUsageStore | None:
    """Build a usage store from environment, or None when not configured.

    Local dev and unit tests skip Supabase entirely - no env vars set,
    middleware is never wired and the server stays reachable without
    side-effects. Cloud Run injects both vars; production always rate-limits.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        return None
    return SupabaseUsageStore(url=url, key=key)
