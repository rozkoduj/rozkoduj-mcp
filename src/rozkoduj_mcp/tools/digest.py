"""MCP tool: market anomaly radar - scan all markets, surface gems."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Market


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def digest(
    market: Market | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Scan global markets and surface anomalies - volume spikes, RSI extremes,
    big moves, 52-week highs/lows, trend strength, and oversold bounces.

    Returns "gems" ranked by surprise score. Includes market pulse (Fear & Greed, VIX).

    Without arguments, scans ALL markets worldwide.
    Pass market="poland" / "crypto" / "us" etc. to focus on one region.
    """
    limit = max(1, min(limit, 100))
    return await scanner.digest(market=market, limit=limit)
