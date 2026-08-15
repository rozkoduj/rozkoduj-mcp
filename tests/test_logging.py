"""Tests for rozkoduj_mcp.logging (structured request logging middleware)."""

import json

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from rozkoduj_mcp.logging import (
    RequestLoggingMiddleware,
    _forwardable,
    current_trace_header,
)


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

    def test_logs_trace_id_from_w3c_traceparent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        resp = client.get(
            "/test",
            headers={
                "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
            },
        )
        assert resp.status_code == 200
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert entry["trace_id"] == "0af7651916cd43dd8448eb211c80319c"

    def test_no_trace_id_when_header_missing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        resp = client.get("/test")
        assert resp.status_code == 200
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        assert "trace_id" not in entry

    def test_no_trace_id_when_traceparent_malformed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # A present-but-unparseable traceparent must fall through cleanly to
        # no trace id, not raise - the header is untrusted inbound data.
        resp = client.get("/test", headers={"traceparent": "garbage"})
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


class TestClientIpAttribution:
    """The logged address must name the caller, not the proxy in front."""

    @staticmethod
    def _logged_ip(capsys: pytest.CaptureFixture[str], **kwargs: object) -> object:
        entry = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
        return entry["ip"]

    def test_uses_rightmost_forwarded_hop(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Only the last hop is appended by the trusted frontend; everything to
        # the left of it is caller-supplied and therefore spoofable.
        client.get(
            "/test",
            headers={"X-Forwarded-For": "203.0.113.9, 70.41.3.18, 150.172.238.178"},
        )
        assert self._logged_ip(capsys) == "150.172.238.178"

    def test_ignores_an_unparsable_forwarded_value(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        client.get("/test", headers={"X-Forwarded-For": "203.0.113.9, not-an-ip"})
        assert self._logged_ip(capsys) == "testclient"

    def test_falls_back_to_the_socket_peer(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        client.get("/test")
        assert self._logged_ip(capsys) == "testclient"


class TestTraceHeaderIsSafeToForward:
    """A forwarded trace header goes back onto the wire, so it is filtered.

    Inbound headers decode as latin-1, so a caller can put bytes in here that
    the outbound client cannot encode. Forwarding one raised a bare
    UnicodeEncodeError out of every tool call in that request.
    """

    def test_accepts_an_ordinary_value(self) -> None:
        assert _forwardable("105445aa7843bc8bf206b120001000/1;o=1") is not None

    def test_rejects_non_ascii(self) -> None:
        assert _forwardable("\xe9abc/0;o=1") is None

    def test_rejects_control_characters(self) -> None:
        assert _forwardable("abc\x01def/0;o=1") is None

    def test_rejects_an_overlong_value(self) -> None:
        assert _forwardable("a" * 201) is None

    def test_a_rejected_header_is_not_bound_for_forwarding(self) -> None:
        seen: list[str | None] = []

        async def _capture(request: Request) -> PlainTextResponse:
            seen.append(current_trace_header.get())
            return PlainTextResponse("ok")

        app = Starlette(
            routes=[Route("/cap", _capture)],
            middleware=[Middleware(RequestLoggingMiddleware)],
        )
        with TestClient(app) as c:
            c.get("/cap", headers={b"X-Cloud-Trace-Context": b"\xe9abc/0;o=1"})
        assert seen == [None]
