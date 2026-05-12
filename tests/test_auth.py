"""Tests for rozkoduj_mcp.auth - JWKS-based JWT verification."""

import base64
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from rozkoduj_mcp.auth import (
    AUDIENCE,
    ISSUER,
    JWKS_URI,
    REQUIRED_SCOPES,
    JWKSTokenVerifier,
    ScopeRequiredError,
    current_scopes,
    current_token_string,
    default_auth,
    requires_scope,
)

_ISSUER = "https://issuer.example"
_AUDIENCE = "https://mcp.example"
_KID = "test-kid"


@pytest.fixture(scope="module")
def keypair() -> tuple[Ed25519PrivateKey, dict[str, Any]]:
    """Generate one Ed25519 keypair per module + matching JWK with kid."""
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    jwk: dict[str, Any] = {
        "kty": "OKP",
        "crv": "Ed25519",
        "kid": _KID,
        "use": "sig",
        "alg": "EdDSA",
        "x": base64.urlsafe_b64encode(public_raw).decode().rstrip("="),
    }
    return private, jwk


def _sign(
    private: Ed25519PrivateKey,
    *,
    iss: str = _ISSUER,
    aud: str = _AUDIENCE,
    scope: str | list[str] = "mcp:read",
    client_id: str = "claude",
    expires_in: int = 3600,
    kid: str | None = _KID,
) -> str:
    """Create an Ed25519-signed JWT for testing."""
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
    return jwt.encode(payload, pem, algorithm="EdDSA", headers=headers)


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
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        result = await verifier.verify_token(_sign(private))
        assert result is not None
        assert result.client_id == "claude"
        assert result.scopes == ["mcp:read"]
        assert result.expires_at is not None

    @pytest.mark.anyio
    async def test_scope_as_list(self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, scope=["mcp:read", "mcp:write"])
        result = await verifier.verify_token(token)
        assert result is not None
        assert set(result.scopes) == {"mcp:read", "mcp:write"}

    @pytest.mark.anyio
    async def test_rejects_wrong_issuer(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, iss="https://attacker.example")
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_wrong_audience(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, aud="https://other.example")
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_expired_token(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, expires_in=-60)
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_accepts_token_within_clock_skew_leeway(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        """Token that expired ~10s ago is still accepted (within 30s leeway)."""
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, expires_in=-10)
        result = await verifier.verify_token(token)
        assert result is not None

    @pytest.mark.anyio
    async def test_rejects_token_with_no_kid(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        private, jwk = keypair
        verifier = _make_verifier(jwk)
        token = _sign(private, kid=None)
        assert await verifier.verify_token(token) is None

    @pytest.mark.anyio
    async def test_rejects_unknown_kid(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
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
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
    ) -> None:
        _, jwk = keypair
        verifier = _make_verifier(jwk)
        assert await verifier.verify_token("not-a-jwt") is None


class TestJWKSRotationRetry:
    """When the auth server rotates its signing key, the cached JWK becomes
    stale until the TTL expires. The verifier must refresh once on signature
    failure so the new key gets picked up immediately.
    """

    @pytest.mark.anyio
    async def test_refreshes_on_signature_failure_and_retries(self) -> None:
        old_key = Ed25519PrivateKey.generate()
        new_key = Ed25519PrivateKey.generate()
        new_pub = new_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        new_jwk: dict[str, Any] = {
            "kty": "OKP",
            "crv": "Ed25519",
            "kid": _KID,
            "alg": "EdDSA",
            "x": base64.urlsafe_b64encode(new_pub).decode().rstrip("="),
        }

        verifier = JWKSTokenVerifier(
            jwks_uri="https://issuer.example/jwks",
            issuer=_ISSUER,
            audience=_AUDIENCE,
        )
        # Seed cache with the *old* public key as if rotation just happened.
        old_pub = old_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        verifier._jwks_keys = {
            _KID: {
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": _KID,
                "alg": "EdDSA",
                "x": base64.urlsafe_b64encode(old_pub).decode().rstrip("="),
            }
        }
        verifier._jwks_fetched_at = time.monotonic()

        async def _swap_to_new_key() -> None:
            verifier._jwks_keys = {_KID: new_jwk}
            verifier._jwks_fetched_at = time.monotonic()

        with patch.object(verifier, "_refresh_jwks", new=AsyncMock(side_effect=_swap_to_new_key)):
            token = _sign(new_key)
            result = await verifier.verify_token(token)

        assert result is not None
        assert result.client_id == "claude"

    @pytest.mark.anyio
    async def test_gives_up_after_one_retry(self) -> None:
        verifier = _make_verifier(
            {
                "kty": "OKP",
                "crv": "Ed25519",
                "kid": _KID,
                "alg": "EdDSA",
                "x": base64.urlsafe_b64encode(
                    Ed25519PrivateKey.generate()
                    .public_key()
                    .public_bytes(
                        encoding=serialization.Encoding.Raw,
                        format=serialization.PublicFormat.Raw,
                    )
                )
                .decode()
                .rstrip("="),
            }
        )
        # Token signed with a totally unrelated key - even after refresh, no match.
        bad_token = _sign(Ed25519PrivateKey.generate())
        with patch.object(verifier, "_refresh_jwks", new=AsyncMock()) as refresh:
            assert await verifier.verify_token(bad_token) is None
        assert refresh.await_count == 1


class TestJWKSFetch:
    @pytest.mark.anyio
    async def test_fetches_jwks_on_first_call(
        self, keypair: tuple[Ed25519PrivateKey, dict[str, Any]]
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
            private = Ed25519PrivateKey.generate()
            assert await verifier.verify_token(_sign(private)) is None


class TestDefaultAuth:
    def test_wires_canonical_endpoints(self) -> None:
        verifier, settings = default_auth()
        assert verifier._issuer == ISSUER
        assert verifier._audience == AUDIENCE
        assert verifier._jwks_uri == JWKS_URI
        assert settings.required_scopes == REQUIRED_SCOPES
        assert str(settings.issuer_url).rstrip("/") == ISSUER.rstrip("/")
        assert str(settings.resource_server_url).rstrip("/") == AUDIENCE.rstrip("/")


def _bind_user(*, scopes: list[str], token: str = "tok") -> Any:  # noqa: S107
    """Bind an AuthenticatedUser to the auth context. Returns the reset handle."""
    user = AuthenticatedUser(AccessToken(token=token, client_id="cli", scopes=scopes))
    return auth_context_var.set(user)


class TestCurrentTokenAccessors:
    def test_no_context_returns_none_and_empty(self) -> None:
        assert current_token_string() is None
        assert current_scopes() == frozenset()

    def test_returns_bound_token_and_scopes(self) -> None:
        reset = _bind_user(scopes=["a", "b"], token="xyz")  # noqa: S106
        try:
            assert current_token_string() == "xyz"
            assert current_scopes() == frozenset({"a", "b"})
        finally:
            auth_context_var.reset(reset)


class TestRequiresScope:
    @pytest.mark.anyio
    async def test_denies_when_scope_missing(self) -> None:
        @requires_scope("mcp:premium")
        async def call() -> str:
            return "ok"

        reset = _bind_user(scopes=["mcp:read"])
        try:
            with pytest.raises(ScopeRequiredError) as exc:
                await call()
            assert exc.value.scope == "mcp:premium"
        finally:
            auth_context_var.reset(reset)

    @pytest.mark.anyio
    async def test_denies_anonymous(self) -> None:
        @requires_scope("mcp:premium")
        async def call() -> str:
            return "ok"

        with pytest.raises(ScopeRequiredError):
            await call()

    @pytest.mark.anyio
    async def test_allows_when_scope_present(self) -> None:
        @requires_scope("mcp:premium")
        async def call(x: int) -> int:
            return x * 2

        reset = _bind_user(scopes=["mcp:read", "mcp:premium"])
        try:
            assert await call(3) == 6
        finally:
            auth_context_var.reset(reset)


class TestScopeRequiredErrorContent:
    """The error message is what FastMCP surfaces to the calling LLM, so it
    has to carry both the actionable login URL and the structured fields
    a chat UI can hook into for a "Log in to unlock" CTA.
    """

    def test_known_scope_resolves_to_premium_tier(self) -> None:
        err = ScopeRequiredError("mcp:knowledge:read")
        assert err.scope == "mcp:knowledge:read"
        assert err.tier_required == "premium"
        assert err.login_url == "https://rozkoduj.com/login"
        assert "log in at https://rozkoduj.com/login" in str(err).lower()
        assert "premium tier" in str(err).lower()

    def test_unknown_scope_falls_back_to_premium(self) -> None:
        err = ScopeRequiredError("mcp:future:write")
        assert err.tier_required == "premium"
        assert "auth_required" in str(err)
