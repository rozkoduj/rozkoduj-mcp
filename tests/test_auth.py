"""Tests for rozkoduj_mcp.auth — JWKS-based JWT verification."""

import base64
import os
import time
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from rozkoduj_mcp.auth import JWKSTokenVerifier, auth_from_env

_ISSUER = "https://issuer.example"
_AUDIENCE = "https://mcp.example"
_KID = "test-kid"


def _b64url_uint(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture(scope="module")
def keypair() -> tuple[RSAPrivateKey, dict[str, Any]]:
    """Generate one RSA keypair per module + matching JWK with kid."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private.public_key().public_numbers()
    jwk: dict[str, Any] = {
        "kty": "RSA",
        "kid": _KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(numbers.n),
        "e": _b64url_uint(numbers.e),
    }
    return private, jwk


def _sign(
    private: RSAPrivateKey,
    *,
    iss: str = _ISSUER,
    aud: str = _AUDIENCE,
    scope: str | list[str] = "mcp:read",
    client_id: str = "claude",
    expires_in: int = 3600,
    kid: str | None = _KID,
) -> str:
    """Create a signed JWT for testing."""
    pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    now = int(time.time())
    payload: dict[str, Any] = {
        "iss": iss,
        "aud": aud,
        "sub": "user-1",
        "client_id": client_id,
        "scope": scope,
        "iat": now,
        "exp": now + expires_in,
    }
    headers = {"kid": kid} if kid else {}
    return jwt.encode(payload, pem, algorithm="RS256", headers=headers)


def _make_verifier(jwk: dict[str, Any]) -> JWKSTokenVerifier:
    verifier = JWKSTokenVerifier(
        jwks_uri="https://issuer.example/jwks",
        issuer=_ISSUER,
        audience=_AUDIENCE,
    )
    verifier._jwks_keys = {_KID: jwk}
    verifier._jwks_fetched_at = time.monotonic()
    return verifier


class TestVerifyToken:
    @pytest.mark.anyio
    async def test_accepts_valid_token(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        result = await verifier.verify_token(_sign(private))
        assert result is not None
        assert result.client_id == "claude"
        assert result.scopes == ["mcp:read"]
        assert result.expires_at is not None

    @pytest.mark.anyio
    async def test_scope_as_list(self, keypair: tuple[RSAPrivateKey, dict[str, Any]]) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, scope=["mcp:read", "mcp:write"])
        result = await verifier.verify_token(token)
        assert result is not None
        assert set(result.scopes) == {"mcp:read", "mcp:write"}

    @pytest.mark.anyio
    async def test_rejects_wrong_issuer(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, iss="https://attacker.example")
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_wrong_audience(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, aud="https://other.example")
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_expired_token(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, expires_in=-60)
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_token_with_no_kid(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, kid=None)
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_unknown_kid(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        # Force refresh to find another unknown kid; mock to return empty.
        with patch.object(JWKSTokenVerifier, "_refresh_jwks", new=AsyncMock()):
            verifier._jwks_keys = {}
            token = _sign(private, kid="other-kid")
            assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_garbage_token(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        _, jwk = keypair
        verifier = _make_verifier(jwk)
        assert await verifier.verify_token("not-a-jwt") is None


class TestJWKSFetch:
    @pytest.mark.anyio
    async def test_fetches_jwks_on_first_call(
        self, keypair: tuple[RSAPrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = JWKSTokenVerifier(
            jwks_uri="https://issuer.example/jwks",
            issuer=_ISSUER,
            audience=_AUDIENCE,
        )
        resp = MagicMock()
        resp.json.return_value = {"keys": [jwk]}
        resp.raise_for_status = MagicMock()
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(return_value=resp)

        with patch("rozkoduj_mcp.auth.httpx.AsyncClient", return_value=client):
            result = await verifier.verify_token(_sign(private))
        assert result is not None
        assert verifier._jwks_keys[_KID]["kid"] == _KID

    @pytest.mark.anyio
    async def test_returns_none_when_jwks_fetch_fails(self) -> None:
        import httpx as _httpx

        verifier = JWKSTokenVerifier(
            jwks_uri="https://issuer.example/jwks",
            issuer=_ISSUER,
            audience=_AUDIENCE,
        )
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(side_effect=_httpx.ConnectError("boom"))

        with patch("rozkoduj_mcp.auth.httpx.AsyncClient", return_value=client):
            # Use a valid-shaped JWT that requires JWKS lookup.
            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            assert await verifier.verify_token(_sign(private)) is None


@pytest.fixture
def clean_auth_env() -> Iterator[None]:
    """Snapshot and restore MCP_AUTH_* env around each test."""
    prefix = "MCP_AUTH_"
    saved = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
    for k in list(os.environ):
        if k.startswith(prefix):
            del os.environ[k]
    try:
        yield
    finally:
        for k in list(os.environ):
            if k.startswith(prefix):
                del os.environ[k]
        os.environ.update(saved)


class TestAuthFromEnv:
    def test_disabled_by_default(self, clean_auth_env: None) -> None:
        assert auth_from_env() is None

    def test_disabled_when_explicitly_false(self, clean_auth_env: None) -> None:
        os.environ["MCP_AUTH_REQUIRED"] = "false"
        assert auth_from_env() is None

    def test_enabled_returns_pair(self, clean_auth_env: None) -> None:
        os.environ["MCP_AUTH_REQUIRED"] = "true"
        os.environ["MCP_AUTH_ISSUER"] = "https://rozkoduj.com"
        os.environ["MCP_AUTH_AUDIENCE"] = "https://mcp.rozkoduj.com"
        result = auth_from_env()
        assert result is not None
        verifier, settings = result
        assert verifier._issuer == "https://rozkoduj.com"
        assert verifier._jwks_uri == "https://rozkoduj.com/jwks"
        assert settings.required_scopes == ["mcp:read"]

    def test_jwks_uri_override(self, clean_auth_env: None) -> None:
        os.environ["MCP_AUTH_REQUIRED"] = "true"
        os.environ["MCP_AUTH_ISSUER"] = "https://rozkoduj.com"
        os.environ["MCP_AUTH_AUDIENCE"] = "https://mcp.rozkoduj.com"
        os.environ["MCP_AUTH_JWKS_URI"] = "https://rozkoduj.com/api/auth/jwks"
        result = auth_from_env()
        assert result is not None
        assert result[0]._jwks_uri == "https://rozkoduj.com/api/auth/jwks"

    def test_custom_scopes(self, clean_auth_env: None) -> None:
        os.environ["MCP_AUTH_REQUIRED"] = "true"
        os.environ["MCP_AUTH_ISSUER"] = "https://rozkoduj.com"
        os.environ["MCP_AUTH_AUDIENCE"] = "https://mcp.rozkoduj.com"
        os.environ["MCP_AUTH_SCOPES"] = "mcp:read mcp:write"
        result = auth_from_env()
        assert result is not None
        assert result[1].required_scopes == ["mcp:read", "mcp:write"]
