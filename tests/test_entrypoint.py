"""Entry-point tests: transport dispatch and HTTP runner configuration."""

from typing import Any

import pytest
import uvicorn
from starlette.applications import Starlette

import rozkoduj_mcp


class TestMainDispatch:
    def test_defaults_to_stdio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MCP_TRANSPORT", raising=False)
        transports: list[str] = []
        monkeypatch.setattr(
            rozkoduj_mcp.mcp, "run", lambda transport: transports.append(transport)
        )

        rozkoduj_mcp.main()

        assert transports == ["stdio"]

    def test_streamable_http_starts_http_server(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
        started: list[bool] = []
        monkeypatch.setattr(rozkoduj_mcp, "_run_http", lambda: started.append(True))

        rozkoduj_mcp.main()

        assert started == [True]

    def test_unknown_transport_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MCP_TRANSPORT", "websocket")
        with pytest.raises(ValueError, match="MCP_TRANSPORT"):
            rozkoduj_mcp.main()


class TestRunHttp:
    def test_binds_default_host_and_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HOST", raising=False)
        monkeypatch.delenv("PORT", raising=False)
        captured: dict[str, Any] = {}

        def fake_run(app: Starlette, host: str, port: int) -> None:
            captured.update(app=app, host=host, port=port)

        monkeypatch.setattr(uvicorn, "run", fake_run)

        rozkoduj_mcp._run_http()

        assert isinstance(captured["app"], Starlette)
        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 8080

    def test_respects_host_and_port_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Cloud Run injects PORT as a string - it must parse to an int.
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("PORT", "9000")
        captured: dict[str, Any] = {}

        def fake_run(app: Starlette, host: str, port: int) -> None:
            captured.update(host=host, port=port)

        monkeypatch.setattr(uvicorn, "run", fake_run)

        rozkoduj_mcp._run_http()

        assert captured["host"] == "127.0.0.1"
        assert captured["port"] == 9000
