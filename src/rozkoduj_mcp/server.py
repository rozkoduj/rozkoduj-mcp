"""MCP server instance for rozkoduj-mcp."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from rozkoduj_mcp.services import scanner

_API_URL = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage httpx client lifecycle - proper startup/shutdown."""
    scanner.setup_client(_API_URL)
    scanner.log_self_host_status()
    try:
        yield None
    finally:
        await scanner.close_client()


_mcp_kwargs: dict[str, Any] = {
    "instructions": (
        "Rozkoduj's own trading intelligence, mirroring the site's pillars: "
        "'leaderboard' - published, backtested strategies ranked by the "
        "Rozkoduj Score (filter by family, or by instrument symbol to answer "
        "'what works best on AAPL?'); 'strategy' - one strategy's full "
        "dossier with its backtest summary (score, APY as cagr local / "
        "cagr_usd cross-market, max_drawdown, "
        "win_rate, risk mode); 'instrument' - the covered-markets catalog, "
        "or with a symbol one instrument's dossier (buy-and-hold facts + the "
        "six-axis character fingerprint); 'research' - one search across the "
        "public articles (returns slug+locale for citation) and, for "
        "signed-in paid tiers, the deeper knowledge corpus."
    ),
    "host": "0.0.0.0",
    "stateless_http": True,
    "json_response": True,
    "lifespan": app_lifespan,
}

mcp = FastMCP("rozkoduj", **_mcp_kwargs)

# Import tool modules so @mcp.tool() decorators register with the server.
import rozkoduj_mcp.tools.instrument as _instrument  # noqa: F401, E402
import rozkoduj_mcp.tools.leaderboard as _leaderboard  # noqa: F401, E402
import rozkoduj_mcp.tools.research as _research  # noqa: F401, E402
import rozkoduj_mcp.tools.strategy as _strategy  # noqa: F401, E402
