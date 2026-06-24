"""rozkoduj-mcp: MCP server for market screening and technical analysis."""

import contextlib
import os
from collections.abc import AsyncIterator
from importlib.metadata import version

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from rozkoduj_mcp.auth import (
    AUDIENCE,
    ISSUER,
    JWTAuthContextMiddleware,
    default_verifier,
)
from rozkoduj_mcp.logging import RequestLoggingMiddleware
from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner

__version__ = version("rozkoduj-mcp")


def main() -> None:
    """Entry point for the MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        _run_http()
    elif transport == "stdio":
        mcp.run(transport="stdio")
    else:
        msg = f"Invalid MCP_TRANSPORT={transport!r}; must be 'stdio' or 'streamable-http'."
        raise ValueError(msg)


async def _robots_txt(request: Request) -> PlainTextResponse:
    return PlainTextResponse("User-agent: *\nDisallow: /\n")


async def _health(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


# SEP-1960 - lightweight server discovery manifest. External MCP clients
# (Claude Desktop, Cursor, others) probe `/.well-known/mcp.json` to
# auto-detect transport, capabilities, and the OAuth authorization server
# without prior configuration.
async def _well_known_mcp(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "mcp_version": "2025-11-25",
            "endpoints": [
                {
                    "url": AUDIENCE,
                    "transport": "streamable-http",
                    "capabilities": ["tools", "resources", "prompts"],
                    "auth": {
                        "type": "oauth2",
                        "authorization_server": ISSUER,
                    },
                }
            ],
        },
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


# RFC 9728 protected-resource metadata.
async def _oauth_protected_resource(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "resource": AUDIENCE,
            "authorization_servers": [ISSUER],
            "scopes_supported": ["mcp:knowledge:read"],
            "bearer_methods_supported": ["header"],
        },
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        },
    )


def build_app() -> Starlette:
    """Build the production Starlette app."""

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        scanner.setup_client(
            os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")
        )
        scanner.log_self_host_status()
        async with mcp.session_manager.run():
            try:
                yield
            finally:
                await scanner.close_client()

    middleware: list[Middleware] = [
        Middleware(RequestLoggingMiddleware),
        Middleware(JWTAuthContextMiddleware, verifier=default_verifier()),
    ]

    return Starlette(
        routes=[
            Route("/robots.txt", _robots_txt),
            Route("/health", _health),
            Route("/.well-known/mcp.json", _well_known_mcp),
            Route(
                "/.well-known/oauth-protected-resource/mcp",
                _oauth_protected_resource,
            ),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        middleware=middleware,
        lifespan=lifespan,
    )


def _run_http() -> None:
    """Run as HTTP server with robots.txt and health endpoints."""
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(build_app(), host=host, port=port)
