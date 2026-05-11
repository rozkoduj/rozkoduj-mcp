"""OAuth 2.1 token verification and per-tool scope gating.

Validates EdDSA JWT access tokens against the rozkoduj.com auth server's
JWKS (RFC 7517) and exposes a ``requires_scope`` decorator that gates
individual tools on the scopes carried by the inbound bearer token. The
issuer, audience, and JWKS URI are constants because this server has one
canonical deployment and one authorization server.
"""

import functools
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

import httpx
import jwt
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

P = ParamSpec("P")
R = TypeVar("R")

# Single accepted signing algorithm. EdDSA / Ed25519 is the modern default
# (RFC 8037): smaller keys, constant-time verify, no padding attacks.
_ACCEPTED_ALGS = ["EdDSA"]

# Production OAuth wiring. One AS, one RS - so the URLs live in code as
# constants rather than env vars. Changing the AS means a code change here.
ISSUER = "https://rozkoduj.com/api/auth"
AUDIENCE = "https://mcp.rozkoduj.com/mcp"
JWKS_URI = f"{ISSUER}/jwks"
REQUIRED_SCOPES = ["mcp:read"]


class JWKSTokenVerifier(TokenVerifier):
    """Verify JWT access tokens against a remote JWKS endpoint."""

    def __init__(
        self,
        *,
        jwks_uri: str,
        issuer: str,
        audience: str,
        jwks_ttl_seconds: float = 3600.0,
        http_timeout: float = 5.0,
    ) -> None:
        self._jwks_uri = jwks_uri
        self._issuer = issuer
        self._audience = audience
        self._jwks_ttl = jwks_ttl_seconds
        self._http_timeout = http_timeout
        self._jwks_keys: dict[str, dict[str, Any]] = {}
        self._jwks_fetched_at: float = 0.0

    async def _refresh_jwks(self) -> None:
        async with httpx.AsyncClient(timeout=self._http_timeout) as client:
            resp = await client.get(self._jwks_uri)
            resp.raise_for_status()
            payload = resp.json()
        keys = payload.get("keys", []) if isinstance(payload, dict) else []
        self._jwks_keys = {k["kid"]: k for k in keys if isinstance(k, dict) and "kid" in k}
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

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not isinstance(kid, str):
                return None
            key = await self._get_signing_key(kid)
            if key is None:
                return None
            payload = jwt.decode(
                token,
                key=key,
                algorithms=_ACCEPTED_ALGS,
                issuer=self._issuer,
                audience=self._audience,
            )
        except jwt.PyJWTError, httpx.HTTPError, ValueError, KeyError:
            return None

        scope_claim = payload.get("scope") or payload.get("scp") or ""
        if isinstance(scope_claim, list):
            scopes = [str(s) for s in scope_claim]
        else:
            scopes = str(scope_claim).split()

        client_id = payload.get("client_id") or payload.get("azp") or ""
        expires_at_raw = payload.get("exp")
        expires_at = int(expires_at_raw) if isinstance(expires_at_raw, (int, float)) else None

        return AccessToken(
            token=token,
            client_id=cast(str, client_id),
            scopes=scopes,
            expires_at=expires_at,
        )


def default_auth() -> tuple[JWKSTokenVerifier, AuthSettings]:
    """Return the verifier + AuthSettings pair for the canonical deployment."""
    verifier = JWKSTokenVerifier(jwks_uri=JWKS_URI, issuer=ISSUER, audience=AUDIENCE)
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER),
        resource_server_url=AnyHttpUrl(AUDIENCE),
        required_scopes=REQUIRED_SCOPES,
    )
    return verifier, settings


def current_scopes() -> frozenset[str]:
    """OAuth scopes from the bearer token bound to the current request.

    Empty when the request is anonymous (no token in flight).
    """
    token = get_access_token()
    if token is None:
        return frozenset()
    return frozenset(token.scopes)


def current_token_string() -> str | None:
    """Raw bearer token string for the current request, when present.

    Used by downstream calls to forward the caller's identity to other
    resource servers rather than relying on a shared transport secret.
    """
    token = get_access_token()
    if token is None:
        return None
    return token.token


class ScopeRequiredError(PermissionError):
    """Raised when the current request is missing a required OAuth scope."""

    def __init__(self, scope: str) -> None:
        super().__init__(f"missing required scope: {scope}")
        self.scope = scope


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
