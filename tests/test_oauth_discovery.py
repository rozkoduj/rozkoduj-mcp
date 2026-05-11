"""RFC 9728 protected-resource discovery wired into the streamable-http app.

These tests pin the discovery surface so regressions in the MCP SDK or our
own wiring don't silently break OAuth clients (Claude Desktop, Cursor) that
rely on `WWW-Authenticate` + `/.well-known/oauth-protected-resource/*` to
locate the authorization server.
"""

from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import pytest
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from starlette.testclient import TestClient

from rozkoduj_mcp.auth import JWKSTokenVerifier

_ISSUER = "https://issuer.example"
_RESOURCE = "https://mcp.example/mcp"
_SCOPES = ["mcp:read", "mcp:knowledge:read"]


@pytest.fixture
def auth_app() -> Iterator[FastMCP]:
    """Build a fresh FastMCP wired with the same auth shape as production."""
    verifier = JWKSTokenVerifier(
        jwks_uri="https://issuer.example/jwks",
        issuer=_ISSUER,
        audience=_RESOURCE,
    )
    settings = AuthSettings(
        issuer_url=AnyHttpUrl(_ISSUER),
        resource_server_url=AnyHttpUrl(_RESOURCE),
        required_scopes=_SCOPES,
    )
    yield FastMCP(
        "rozkoduj-test",
        stateless_http=True,
        json_response=True,
        token_verifier=verifier,
        auth=settings,
    )


def _client(server: FastMCP) -> TestClient:
    return TestClient(server.streamable_http_app())


class TestProtectedResourceMetadata:
    def test_returns_rfc9728_metadata(self, auth_app: FastMCP) -> None:
        with _client(auth_app) as client:
            resp = client.get("/.well-known/oauth-protected-resource/mcp")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["resource"].rstrip("/") == _RESOURCE.rstrip("/")
        assert [str(u).rstrip("/") for u in body["authorization_servers"]] == [_ISSUER]
        assert set(body["scopes_supported"]) == set(_SCOPES)
        assert "header" in body["bearer_methods_supported"]


class TestUnauthenticatedChallenge:
    def test_anonymous_request_returns_401_with_resource_metadata(self, auth_app: FastMCP) -> None:
        with _client(auth_app) as client:
            resp = client.post(
                "/mcp",
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            )
        assert resp.status_code == 401
        challenge = resp.headers.get("www-authenticate", "")
        assert challenge.startswith("Bearer "), challenge
        # The metadata URL embedded in the challenge must point at the same
        # resource we advertise so clients can chain discovery without guessing.
        assert 'resource_metadata="' in challenge
        marker = 'resource_metadata="'
        start = challenge.index(marker) + len(marker)
        end = challenge.index('"', start)
        metadata_url = challenge[start:end]
        parsed = urlparse(metadata_url)
        assert parsed.path == "/.well-known/oauth-protected-resource/mcp"


def test_disabled_auth_skips_protected_resource_route() -> None:
    """Without auth settings the SDK must not advertise an RS - tools stay open."""
    server = FastMCP("rozkoduj-test-open", stateless_http=True, json_response=True)
    paths = {getattr(r, "path", None) for r in server.streamable_http_app().routes}
    assert "/.well-known/oauth-protected-resource/mcp" not in paths
    assert "/mcp" in paths
