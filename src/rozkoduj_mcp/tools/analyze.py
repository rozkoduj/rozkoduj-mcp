"""MCP tool: single-symbol technical analysis."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service
from rozkoduj_mcp.tools import Interval


@mcp.tool()
async def analyze(
    symbol: str,
    interval: Interval = "1d",
) -> dict[str, Any]:
    """Get technical analysis for a symbol.

    Auto-detects exchange. Returns composite rating plus detailed indicators.
    """
    return await ta_service.get_analysis(symbol, interval)
