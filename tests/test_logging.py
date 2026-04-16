"""Tests for rozkoduj_mcp.logging (structured request logging middleware)."""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from rozkoduj_mcp.logging import RequestLoggingMiddleware


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
