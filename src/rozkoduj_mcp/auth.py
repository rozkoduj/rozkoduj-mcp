"""OAuth 2.1 token verification and per-tool scope gating.

Validates RS256 JWT access tokens against a remote JWKS (RFC 7517) and
provides a ``requires_scope`` decorator that gates individual tools on
the OAuth scopes carried by the inbound bearer token. The JWKS is fetched
lazily on first use and cached per process. Wiring lives in ``server.py``
and is gated by ``MCP_AUTH_REQUIRED`` so the server can run anonymously
by default during the rollout.
"""

import functools
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, cast

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

P = ParamSpec("P")
R = TypeVar("R")


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
        return RSAAlgorithm.from_jwk(jwk)

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
                algorithms=["RS256"],
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


def auth_from_env() -> tuple[JWKSTokenVerifier, AuthSettings] | None:
    """Build a verifier + AuthSettings pair from env, or return None when disabled.

    Required when MCP_AUTH_REQUIRED=true:
        MCP_AUTH_ISSUER     OAuth issuer URL (matches the `iss` JWT claim)
        MCP_AUTH_AUDIENCE   Resource server URL (matches the `aud` JWT claim)
    Optional:
        MCP_AUTH_JWKS_URI   Defaults to <issuer>/jwks
        MCP_AUTH_SCOPES     Space-separated list (defaults to "mcp:read")
    """
    if not is_auth_active():
        return None

    issuer = os.environ["MCP_AUTH_ISSUER"]
    audience = os.environ["MCP_AUTH_AUDIENCE"]
    jwks_uri = os.environ.get("MCP_AUTH_JWKS_URI") or f"{issuer.rstrip('/')}/jwks"
    required_scopes = os.environ.get("MCP_AUTH_SCOPES", "mcp:read").split()

    verifier = JWKSTokenVerifier(jwks_uri=jwks_uri, issuer=issuer, audience=audience)
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(issuer),
        resource_server_url=AnyHttpUrl(audience),
        required_scopes=required_scopes,
    )
    return verifier, settings


def is_auth_active() -> bool:
    """Return True when token verification is enforced for this process."""
    return os.environ.get("MCP_AUTH_REQUIRED", "").lower() == "true"


def current_scopes() -> frozenset[str]:
    """OAuth scopes from the bearer token bound to the current request.

    Empty when the request is anonymous (no token or auth disabled).
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

    No-op while ``MCP_AUTH_REQUIRED`` is unset so the server keeps serving
    anonymously during the rollout. Once auth is enforced, calls without
    the required scope raise ``ScopeRequiredError`` which the MCP layer
    surfaces as a tool error.
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if is_auth_active() and scope not in current_scopes():
                raise ScopeRequiredError(scope)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
