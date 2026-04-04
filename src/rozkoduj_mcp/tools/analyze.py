"""MCP tool: single-symbol technical analysis."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Interval, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def analyze(
    symbol: str,
    interval: Interval = "1d",
) -> dict[str, Any]:
    """Get technical analysis for a symbol.

    Auto-detects exchange. Returns composite rating plus detailed indicators.
    """
    validate_str(symbol, "symbol")
    return await ta_service.get_analysis(symbol, interval)
