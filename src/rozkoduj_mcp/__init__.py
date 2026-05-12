"""rozkoduj-mcp: MCP server for market screening and technical analysis."""

import os
from importlib.metadata import version

__version__ = version("rozkoduj-mcp")


def main() -> None:
    """Entry point for the MCP server."""
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        _run_http()
    elif transport == "stdio":
        from rozkoduj_mcp.server import mcp

        mcp.run(transport="stdio")
    else:
        msg = f"Invalid MCP_TRANSPORT={transport!r}; must be 'stdio' or 'streamable-http'."
        raise ValueError(msg)


def _run_http() -> None:
    """Run as HTTP server with robots.txt and health endpoints."""
    import contextlib
    from collections.abc import AsyncIterator

    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse, PlainTextResponse
    from starlette.routing import Mount, Route

    from rozkoduj_mcp.auth import AUDIENCE, ISSUER
    from rozkoduj_mcp.logging import RequestLoggingMiddleware
    from rozkoduj_mcp.server import mcp
    from rozkoduj_mcp.services import scanner

    async def robots_txt(request: Request) -> PlainTextResponse:
        return PlainTextResponse("User-agent: *\nDisallow: /\n")

    async def health(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    # SEP-1960 - lightweight server discovery manifest. External MCP
    # clients (Claude Desktop, Cursor, others) probe `/.well-known/mcp.json`
    # to auto-detect transport, capabilities, and the OAuth authorization
    # server without prior configuration. The protected-resource metadata
    # (RFC 9728) is still mounted by the FastMCP transport at
    # `/.well-known/oauth-protected-resource/mcp` for the OAuth handshake.
    async def well_known_mcp(request: Request) -> JSONResponse:
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

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        scanner.setup_client(os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com"))
        async with mcp.session_manager.run():
            try:
                yield
            finally:
                await scanner.close_client()

    middleware: list[Middleware] = [Middleware(RequestLoggingMiddleware)]

    app = Starlette(
        routes=[
            Route("/robots.txt", robots_txt),
            Route("/health", health),
            Route("/.well-known/mcp.json", well_known_mcp),
            Mount("/", app=mcp.streamable_http_app()),
        ],
        middleware=middleware,
        lifespan=lifespan,
    )

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host=host, port=port)
