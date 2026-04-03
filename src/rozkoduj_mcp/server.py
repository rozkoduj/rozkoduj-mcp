"""MCP server instance for rozkoduj-mcp."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP

from rozkoduj_mcp.services import scanner

_API_URL = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage httpx client lifecycle — proper startup/shutdown."""
    scanner.client = httpx.AsyncClient(base_url=_API_URL, timeout=20.0)
    try:
        yield None
    finally:
        await scanner.client.aclose()
        scanner.client = None


mcp = FastMCP(
    "rozkoduj",
    instructions=(
        "Market screening and technical analysis for stocks, crypto, and forex. "
        "Use 'scan' to screen markets, 'analyze' for single-symbol TA, "
        "'score' for holistic 0-100 scoring, 'movers' for top gainers/losers, "
        "'compare' for multi-symbol comparison, 'multitf' for multi-timeframe analysis."
    ),
    host="0.0.0.0",
    stateless_http=True,
    json_response=True,
    lifespan=app_lifespan,
)

# Import tool modules so @mcp.tool() decorators register with the server.
import rozkoduj_mcp.tools.analyze as _analyze  # noqa: F401, E402
import rozkoduj_mcp.tools.compare as _compare  # noqa: F401, E402
import rozkoduj_mcp.tools.movers as _movers  # noqa: F401, E402
import rozkoduj_mcp.tools.multitf as _multitf  # noqa: F401, E402
import rozkoduj_mcp.tools.scan as _scan  # noqa: F401, E402
import rozkoduj_mcp.tools.score as _score  # noqa: F401, E402
