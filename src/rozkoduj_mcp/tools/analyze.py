"""MCP tool: single-symbol technical analysis."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service

Interval = Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1W", "1M"]


@mcp.tool()
async def analyze(
    symbol: str,
    interval: Interval = "1d",
) -> dict[str, Any]:
    """Get technical analysis for a symbol.

    Auto-detects exchange. Returns composite rating plus detailed indicators.
    """
    return await ta_service.get_analysis(symbol, "", "", interval)
