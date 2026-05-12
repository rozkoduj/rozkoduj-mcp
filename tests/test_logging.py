"""Tests for rozkoduj_mcp.logging (structured request logging middleware)."""

import json

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from rozkoduj_mcp.logging import RequestLoggingMiddleware, current_trace_header


async def _ok(request: Request) -> JSONResponse:
    return JSONResponse({"ok": True})


async def _health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


async def _robots(request: Request) -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


async def _fail(request: Request) -> None:
    msg = "boom"
    raise ValueError(msg)


def _make_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/test", _ok),
            Route("/health", _health),
            Route("/robots.txt", _robots),
            Route("/fail", _fail),
        ],
        middleware=[Middleware(RequestLoggingMiddleware)],
    )


client = TestClient(_make_app(), raise_server_exceptions=False)


class TestRequestLogging:
    def test_logs_successful_request(self) -> None:
        resp = client.get("/test")
        assert resp.status_code == 200

    def test_skips_health(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_skips_robots(self) -> None:
        resp = client.get("/robots.txt")
        assert resp.status_code == 200

    def test_logs_error_status(self) -> None:
        resp = client.get("/fail")
        assert resp.status_code == 500

    def test_logs_404(self) -> None:
        resp = client.get("/nonexistent")
        assert resp.status_code == 404


class TestTracePropagation:
    """Trace correlation: Cloud Run injects ``X-Cloud-Trace-Context`` on every
    request; the middleware logs the trace id and exposes the raw header so
    downstream HTTP calls can forward it for joined log views.
    """

    def test_logs_trace_id_from_cloud_trace_header(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        resp = client.get(
            "/test",
            headers={"X-Cloud-Trace-Context": "abc123def/0;o=1"},
        )
        assert resp.status_code == 200
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert entry["trace_id"] == "abc123def"

    def test_logs_trace_id_from_w3c_traceparent(self, capsys: pytest.CaptureFixture[str]) -> None:
        resp = client.get(
            "/test",
            headers={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"},
        )
        assert resp.status_code == 200
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert entry["trace_id"] == "0af7651916cd43dd8448eb211c80319c"

    def test_no_trace_id_when_header_missing(self, capsys: pytest.CaptureFixture[str]) -> None:
        resp = client.get("/test")
        assert resp.status_code == 200
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert "trace_id" not in entry

    def test_exposes_raw_header_via_contextvar(self) -> None:
        """Downstream callers read ``current_trace_header`` to forward it."""
        seen: list[str | None] = []

        async def _capture(request: Request) -> PlainTextResponse:
            seen.append(current_trace_header.get())
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/cap", _capture)],
            middleware=[Middleware(RequestLoggingMiddleware)],
        )
        with TestClient(app) as c:
            c.get("/cap", headers={"X-Cloud-Trace-Context": "xyz/0;o=1"})
        assert seen == ["xyz/0;o=1"]
        # Reset after the request completes - leak would poison the next call.
        assert current_trace_header.get() is None
