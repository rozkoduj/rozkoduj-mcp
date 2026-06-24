"""JWT identity extraction and per-tool scope gating."""

import functools
import ipaddress
import logging
import time
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any, ParamSpec, TypeVar

import httpx
import jwt
from mcp.server.auth.provider import AccessToken, TokenVerifier
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

# Request-scoped identity extracted from the validated JWT. Empty string
# (never None) so outbound headers built from these values stay clean.
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")
current_user_tier: ContextVar[str] = ContextVar("current_user_tier", default="")
current_user_scopes: ContextVar[str] = ContextVar("current_user_scopes", default="")
# End-client IP (last X-Forwarded-For hop) — forwarded to the data API as
# X-Client-Ip so anonymous quota buckets key on the real client, not this
# service's egress IP (which would be one shared bucket for all anon users).
current_client_ip: ContextVar[str] = ContextVar("current_client_ip", default="")

# Subscription tiers this server recognises. Used only to sanitize an inbound
# tier claim - an unrecognised value is never treated as one of these.
TIERS: frozenset[str] = frozenset({"anon", "free", "pro", "max"})


def normalize_tier(raw: str | None) -> str:
    """Return ``raw`` when it is a known tier, else ``anon`` (logged for a
    present-but-unknown value).

    A malformed or unrecognised tier must never be treated as a higher tier
    than it is. ``None`` / empty (a genuinely anonymous request) degrade quietly.
    """
    if raw is not None and raw in TIERS:
        return raw
    if raw:
        logger.warning("unknown_tier_degraded_to_anon", extra={"tier": raw})
    return "anon"


# Single accepted signing algorithm. EdDSA / Ed25519 is the modern default
# (RFC 8037): smaller keys, constant-time verify, no padding attacks.
_ACCEPTED_ALGS = ["EdDSA"]

# Production OAuth wiring. One AS, one RS - so the URLs live in code as
# constants rather than env vars. Changing the AS means a code change here.
ISSUER = "https://www.rozkoduj.com/api/auth"
AUDIENCE = "https://mcp.rozkoduj.com/mcp"
JWKS_URI = f"{ISSUER}/jwks"

# Embedded in scope-required errors so the calling LLM can surface a
# login link to the end user.
LOGIN_URL = "https://rozkoduj.com/login"


class JWKSTokenVerifier(TokenVerifier):
    """Verify JWT access tokens against a remote JWKS endpoint."""

    def __init__(
        self,
        *,
        jwks_uri: str,
        issuer: str,
        audience: str,
        jwks_ttl_seconds: float = 3600.0,
        jwks_refresh_cooldown_seconds: float = 30.0,
        http_timeout: float = 5.0,
    ) -> None:
        self._jwks_uri = jwks_uri
        self._issuer = issuer
        self._audience = audience
        self._jwks_ttl = jwks_ttl_seconds
        self._jwks_cooldown = jwks_refresh_cooldown_seconds
        self._http_timeout = http_timeout
        self._jwks_keys: dict[str, dict[str, Any]] = {}
        self._jwks_fetched_at: float = 0.0
        self._jwks_attempted_at: float | None = None

    async def _refresh_jwks(self) -> None:
        # Unknown kids and signature failures trigger a refresh, so without
        # a cooldown a flood of garbage tokens would turn into one fetch
        # against the authorization server per request. Worst case a freshly
        # rotated key waits one cooldown before it is picked up.
        now = time.monotonic()
        if (
            self._jwks_attempted_at is not None
            and (now - self._jwks_attempted_at) < self._jwks_cooldown
        ):
            return
        # Stamped before the fetch so failed attempts burn the cooldown too -
        # an unreachable JWKS endpoint must not get hammered either.
        self._jwks_attempted_at = now
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            resp = await client.get(self._jwks_uri)
            resp.raise_for_status()
            payload = resp.json()
        keys = payload.get("keys", []) if isinstance(payload, dict) else []
        self._jwks_keys = {
            k["kid"]: k for k in keys if isinstance(k, dict) and "kid" in k
        }
        self._jwks_fetched_at = time.monotonic()

    async def _get_signing_key(self, kid: str) -> Any:
        now = time.monotonic()
        stale = (now - self._jwks_fetched_at) > self._jwks_ttl
        if not self._jwks_keys or stale or kid not in self._jwks_keys:
            await self._refresh_jwks()
        jwk = self._jwks_keys.get(kid)
        if jwk is None:
            return None
        # PyJWK auto-selects the algorithm class from `kty` so RSA, OKP
        # (Ed25519/Ed448), and EC keys all work without per-type branching.
        return jwt.PyJWK(jwk).key

    async def _decode_with_rotation_retry(
        self, token: str, kid: str
    ) -> dict[str, Any] | None:
        """Decode ``token``, force-refreshing the JWKS once on signature failure
        so a freshly rotated signing key is picked up before the cached TTL
        expires.
        """
        for attempt in range(2):
            key = await self._get_signing_key(kid)
            if key is None:
                return None
            try:
                return jwt.decode(
                    token,
                    key=key,
                    algorithms=_ACCEPTED_ALGS,
                    issuer=self._issuer,
                    audience=self._audience,
                    leeway=30,
                )
            except jwt.InvalidSignatureError:
                if attempt == 1:
                    return None
                await self._refresh_jwks()
        return None  # pragma: no cover

    async def verify_token(self, token: str) -> AccessToken | None:
        # A rejected bearer silently degrades the request to anonymous, so
        # every rejection path leaves a log trail for production debugging.
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not isinstance(kid, str):
                logger.warning("token_rejected", extra={"reason": "missing kid"})
                return None
            payload = await self._decode_with_rotation_retry(token, kid)
            if payload is None:
                logger.warning(
                    "token_rejected",
                    extra={"reason": "no matching signing key or bad signature"},
                )
                return None
        except (jwt.PyJWTError, httpx.HTTPError, ValueError, KeyError) as exc:
            logger.warning("token_rejected", extra={"reason": repr(exc)})
            return None

        scope_claim = payload.get("scope") or payload.get("scp") or ""
        if isinstance(scope_claim, list):
            scopes = [str(s) for s in scope_claim]
        else:
            scopes = str(scope_claim).split()

        expires_at_raw = payload.get("exp")
        expires_at = (
            int(expires_at_raw) if isinstance(expires_at_raw, (int, float)) else None
        )

        # Missing claims stay empty - no defaults injected. An unknown tier
        # claim is normalized to anon rather than trusted verbatim.
        tier_claim = payload.get("tier")
        current_user_id.set(str(payload.get("sub") or ""))
        current_user_tier.set(normalize_tier(str(tier_claim)) if tier_claim else "")
        current_user_scopes.set(" ".join(scopes))

        return AccessToken(
            token=token,
            client_id=str(payload.get("client_id") or payload.get("azp") or ""),
            scopes=scopes,
            expires_at=expires_at,
        )


def _trusted_client_ip(forwarded_for: str) -> str:
    """End-client IP from X-Forwarded-For: rightmost entry, validated.

    Cloud Run's frontend APPENDS the connecting client's IP and does not
    strip client-supplied entries, so only the LAST hop is trustworthy —
    the leftmost value is attacker-controlled (a spoofed header would let
    an anonymous client rotate quota buckets at will). Assumes direct
    Cloud Run ingress (no LB in front); returns "" when the value does
    not parse as an IP, so garbage never becomes a quota bucket.
    """
    candidate = forwarded_for.rsplit(",", 1)[-1].strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return ""
    return candidate


class JWTAuthContextMiddleware:
    """ASGI middleware that tags a request with verified JWT identity."""

    def __init__(self, app: ASGIApp, verifier: JWKSTokenVerifier) -> None:
        self._app = app
        self._verifier = verifier

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        auth_header = ""
        forwarded_for: list[str] = []
        for name, value in scope.get("headers", []):
            if name == b"authorization" and not auth_header:
                auth_header = value.decode("latin-1", errors="ignore")
            elif name == b"x-forwarded-for":
                forwarded_for.append(value.decode("latin-1", errors="ignore"))
        client_ip = _trusted_client_ip(",".join(forwarded_for))

        # Bind identity to the anonymous default up front and keep the reset
        # tokens. verify_token overwrites these for an authenticated request;
        # the finally restores the pre-request state via the same Token
        # discipline as RequestLoggingMiddleware, so identity can never bleed
        # into a later request that reuses this context.
        id_token = current_user_id.set("")
        tier_token = current_user_tier.set("")
        scopes_token = current_user_scopes.set("")
        ip_token = current_client_ip.set(client_ip)
        try:
            if auth_header.lower().startswith("bearer "):
                # verify_token sets the ContextVars; return value unused.
                await self._verifier.verify_token(auth_header[7:])

            await self._app(scope, receive, send)
        finally:
            current_user_id.reset(id_token)
            current_user_tier.reset(tier_token)
            current_user_scopes.reset(scopes_token)
            current_client_ip.reset(ip_token)


def default_verifier() -> JWKSTokenVerifier:
    """JWT verifier wired against the canonical authorization server."""
    return JWKSTokenVerifier(jwks_uri=JWKS_URI, issuer=ISSUER, audience=AUDIENCE)


def current_scopes() -> frozenset[str]:
    """OAuth scopes from the bearer token bound to the current request.

    Empty when the request is anonymous (no token in flight).
    """
    raw = current_user_scopes.get()
    if not raw:
        return frozenset()
    return frozenset(raw.split())


class ScopeRequiredError(PermissionError):
    """Raised when the current request is missing a required OAuth scope.

    The string form is surfaced as the tool error a calling LLM sees,
    so the embedded login URL doubles as the actionable hint.
    """

    def __init__(self, scope: str) -> None:
        self.scope = scope
        self.login_url = LOGIN_URL
        message = (
            f"auth_required: this tool needs the '{scope}' scope. "
            f"Unlock at {LOGIN_URL}."
        )
        super().__init__(message)


def requires_scope(
    scope: str,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Gate a tool on an OAuth scope carried by the inbound bearer token.

    Anonymous calls (no token) and calls whose token lacks the scope both
    raise ``ScopeRequiredError`` which the MCP layer surfaces as a tool
    error.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if scope not in current_scopes():
                raise ScopeRequiredError(scope)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
