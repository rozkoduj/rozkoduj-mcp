"""MCP server instance for rozkoduj-mcp."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from rozkoduj_mcp.auth import default_auth
from rozkoduj_mcp.services import scanner

_API_URL = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[None]:
    """Manage httpx client lifecycle - proper startup/shutdown."""
    scanner.setup_client(_API_URL)
    try:
        yield None
    finally:
        await scanner.close_client()


_mcp_kwargs: dict[str, Any] = {
    "instructions": (
        "Market screening and technical analysis for stocks, crypto, and forex. "
        "Use 'digest' to scan all global markets and surface anomalies (gems) - "
        "volume spikes, RSI extremes, big moves, 52-week highs/lows. "
        "Use 'scan' to screen markets, 'analyze' for single-symbol TA, "
        "'score' for holistic 0-100 scoring, 'fundamentals' for valuation and analyst data, "
        "'buzz' for per-ticker attention signal, "
        "'market_pulse' for market regime (RISK-ON/OFF), "
        "'calendar' for economic events, 'smart_screen' for preset screens "
        "(unusual_volume, oversold_bounce, breakout, momentum, value, dividend, growth), "
        "'movers' for top gainers/losers, 'compare' for multi-symbol comparison, "
        "'multitf' for multi-timeframe analysis. "
        "For Rozkoduj's own published trading strategies (the leaderboard at "
        "rozkoduj.com): use 'list_strategies' to browse the catalog and "
        "'strategy_details' to drill into one - returns name, description, "
        "tags, family/variant, and best_run metrics (sharpe, sortino, cagr, "
        "max_drawdown, win_rate). "
        "For free-text questions about Rozkoduj content: use 'search_articles' "
        "to query the public blog (returns slug+locale for citation). "
        "Every market-data response carries a data freshness contract (data_date, "
        "freshness, staleness_seconds, fetched_at) - read the "
        "rozkoduj://freshness-contract resource for the full schema and reasoning "
        "guidance."
    ),
    "host": "0.0.0.0",
    "stateless_http": True,
    "json_response": True,
    "lifespan": app_lifespan,
}

_verifier, _auth_settings = default_auth()
_mcp_kwargs["token_verifier"] = _verifier
_mcp_kwargs["auth"] = _auth_settings

mcp = FastMCP("rozkoduj", **_mcp_kwargs)

# Import tool modules so @mcp.tool() decorators register with the server.
# Import resources and prompts so @mcp.resource()/@mcp.prompt() decorators register.
import rozkoduj_mcp.prompts as _prompts  # noqa: F401, E402
import rozkoduj_mcp.resources as _resources  # noqa: F401, E402
import rozkoduj_mcp.tools.analyze as _analyze  # noqa: F401, E402
import rozkoduj_mcp.tools.buzz as _buzz  # noqa: F401, E402
import rozkoduj_mcp.tools.calendar as _calendar  # noqa: F401, E402
import rozkoduj_mcp.tools.compare as _compare  # noqa: F401, E402
import rozkoduj_mcp.tools.decode as _decode  # noqa: F401, E402
import rozkoduj_mcp.tools.digest as _digest  # noqa: F401, E402
import rozkoduj_mcp.tools.fundamentals as _fundamentals  # noqa: F401, E402
import rozkoduj_mcp.tools.list_strategies as _list_strategies  # noqa: F401, E402
import rozkoduj_mcp.tools.market_pulse as _market_pulse  # noqa: F401, E402
import rozkoduj_mcp.tools.movers as _movers  # noqa: F401, E402
import rozkoduj_mcp.tools.multitf as _multitf  # noqa: F401, E402
import rozkoduj_mcp.tools.scan as _scan  # noqa: F401, E402
import rozkoduj_mcp.tools.score as _score  # noqa: F401, E402
import rozkoduj_mcp.tools.search_articles as _search_articles  # noqa: F401, E402
import rozkoduj_mcp.tools.search_knowledge as _search_knowledge  # noqa: F401, E402
import rozkoduj_mcp.tools.smart_screen as _smart_screen  # noqa: F401, E402
import rozkoduj_mcp.tools.strategy_details as _strategy_details  # noqa: F401, E402
