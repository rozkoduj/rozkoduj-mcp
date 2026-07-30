"""rozkoduj-mcp: MCP server for Rozkoduj's published trading strategies and knowledge base."""

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
from rozkoduj_mcp.server import TRANSPORT_SECURITY, mcp

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


# RFC 9728 protected-resource metadata. This is the one spec-backed discovery
# path and the only one a client is guaranteed to consume: the draft .well-known
# manifest proposals (SEP-1649 / SEP-1960) remain unmerged, and the 2026-07-28
# revision went a different way entirely - server discovery there is a
# `server/discover` RPC, not a well-known document.
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

    # The data-API client is owned solely by the server's own lifespan, which
    # session_manager.run() drives. Setting it up here as well used to be
    # harmless because the stateless transport re-entered that lifespan per
    # request; it now runs once per session manager, so a second setup here
    # would orphan an unclosed client for the life of the process.
    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with mcp.session_manager.run():
            yield

    middleware: list[Middleware] = [
        Middleware(RequestLoggingMiddleware),
        Middleware(JWTAuthContextMiddleware, verifier=default_verifier()),
    ]

    return Starlette(
        routes=[
            Route("/robots.txt", _robots_txt),
            Route("/health", _health),
            Route(
                "/.well-known/oauth-protected-resource/mcp",
                _oauth_protected_resource,
            ),
            Mount(
                "/",
                app=mcp.streamable_http_app(
                    stateless_http=True,
                    json_response=True,
                    transport_security=TRANSPORT_SECURITY,
                ),
            ),
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
