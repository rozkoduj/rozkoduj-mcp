"""Discovery routes and anonymous-pass-through tests."""

from collections.abc import Iterator
from typing import Any, ClassVar

import pytest
from mcp.types import LATEST_PROTOCOL_VERSION
from starlette.testclient import TestClient

from rozkoduj_mcp import build_app
from rozkoduj_mcp.auth import AUDIENCE, ISSUER


# Module-scoped: the session manager only enters its lifespan once per process.
# base_url picks a host on the transport-security allowlist (the default
# "testserver" is deliberately NOT allowed - see TestTransportSecurity).
@pytest.fixture(scope="module")
def app_client() -> Iterator[TestClient]:
    with TestClient(build_app(), base_url="http://localhost") as client:
        yield client


class TestProtectedResourceMetadata:
    def test_returns_rfc9728_metadata(self, app_client: TestClient) -> None:
        resp = app_client.get("/.well-known/oauth-protected-resource/mcp")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["resource"].rstrip("/") == AUDIENCE.rstrip("/")
        assert body["authorization_servers"] == [ISSUER]
        assert body["scopes_supported"] == ["mcp:knowledge:read"]
        assert "header" in body["bearer_methods_supported"]


class TestServerManifest:
    def test_advertises_endpoint_transport_and_auth(
        self, app_client: TestClient
    ) -> None:
        resp = app_client.get("/.well-known/mcp.json")
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["mcp_version"] == LATEST_PROTOCOL_VERSION
        endpoint = body["endpoints"][0]
        assert endpoint["url"] == AUDIENCE
        assert endpoint["transport"] == "streamable-http"
        assert endpoint["auth"]["authorization_server"] == ISSUER
        assert set(endpoint["capabilities"]) == {"tools"}
        assert resp.headers["cache-control"] == "public, max-age=3600"


class TestServiceRoutes:
    def test_health_answers_ok(self, app_client: TestClient) -> None:
        resp = app_client.get("/health")
        assert resp.status_code == 200
        assert resp.text == "ok"

    def test_robots_disallows_crawling(self, app_client: TestClient) -> None:
        resp = app_client.get("/robots.txt")
        assert resp.status_code == 200
        assert "Disallow: /" in resp.text


class TestAnonymousPassThrough:
    def test_anonymous_request_is_not_rejected_at_transport(
        self, app_client: TestClient
    ) -> None:
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"Accept": "application/json, text/event-stream"},
        )
        assert resp.status_code != 401
        assert "www-authenticate" not in {k.lower() for k in resp.headers}


class TestTransportSecurity:
    """Host/Origin validation on the MCP transport (spec 2025-11-25)."""

    def test_unknown_host_rejected(self, app_client: TestClient) -> None:
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={
                "Accept": "application/json, text/event-stream",
                "Host": "evil.example",
            },
        )
        assert resp.status_code == 421

    def test_cross_origin_rejected(self, app_client: TestClient) -> None:
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={
                "Accept": "application/json, text/event-stream",
                "Origin": "https://evil.example",
            },
        )
        assert resp.status_code == 403


class TestInvalidBearerChallenge:
    """A presented-and-rejected bearer must get a 401 challenge (RFC 9728);
    the discovery endpoints stay exempt so OAuth can bootstrap."""

    # Structurally invalid JWT: header parsing fails locally, so the
    # verifier rejects without ever fetching the remote JWKS.
    _BAD_AUTH: ClassVar[dict[str, str]] = {"Authorization": "Bearer not-a-jwt"}

    def test_invalid_bearer_gets_401_challenge(self, app_client: TestClient) -> None:
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={"Accept": "application/json, text/event-stream", **self._BAD_AUTH},
        )
        assert resp.status_code == 401
        challenge = resp.headers["WWW-Authenticate"]
        assert challenge.startswith("Bearer ")
        assert 'error="invalid_token"' in challenge
        assert "/.well-known/oauth-protected-resource/mcp" in challenge

    def test_invalid_bearer_on_discovery_passes(self, app_client: TestClient) -> None:
        resp = app_client.get(
            "/.well-known/oauth-protected-resource/mcp", headers=self._BAD_AUTH
        )
        assert resp.status_code == 200
