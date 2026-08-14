"""Discovery routes and anonymous-pass-through tests."""

from collections.abc import Iterator
from typing import Any, ClassVar

import pytest
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

    def test_production_host_accepted(self, app_client: TestClient) -> None:
        # The rejection tests below pass just as happily against a
        # localhost-only allowlist, which is exactly what the transport falls
        # back to when the app is built without explicit settings. Only a
        # positive assertion on the real deployed host tells the two apart -
        # otherwise that misconfiguration ships green and 421s every request
        # in production.
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            headers={
                "Accept": "application/json, text/event-stream",
                "Host": "mcp.rozkoduj.com",
            },
        )
        assert resp.status_code == 200
        # A plain JSON body (not an SSE stream) proves the response-mode flag
        # survived the move out of the constructor as well.
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json()["result"]["tools"]

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


class TestStandaloneStreamNotOffered:
    """GET on the protocol endpoint.

    The transport runs stateless with JSON responses, so the spec's optional
    server-to-client stream carries nothing. Answering 405 tells a client that
    once; without it the SDK accepts the GET and holds the connection on
    keepalives until the platform cuts it, so every client that opens the
    stream reconnects on a loop.
    """

    def test_get_is_refused_with_405(self, app_client: TestClient) -> None:
        resp = app_client.get("/mcp")
        assert resp.status_code == 405
        assert resp.headers["allow"] == "POST"

    def test_post_still_reaches_the_transport(self, app_client: TestClient) -> None:
        # The GET-only route must partial-match and fall through, not shadow
        # the mounted transport that serves the protocol.
        resp = app_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        assert resp.status_code == 200
        assert "result" in resp.json()
