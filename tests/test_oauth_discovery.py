"""Discovery routes and anonymous-pass-through tests."""

from collections.abc import Iterator
from typing import Any

import pytest
from starlette.testclient import TestClient

from rozkoduj_mcp import build_app
from rozkoduj_mcp.auth import AUDIENCE, ISSUER


# Module-scoped: the session manager only enters its lifespan once per process.
@pytest.fixture(scope="module")
def app_client() -> Iterator[TestClient]:
    with TestClient(build_app()) as client:
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
