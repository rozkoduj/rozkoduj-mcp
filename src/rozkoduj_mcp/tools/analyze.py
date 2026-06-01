"""MCP tool: single-symbol technical analysis."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Interval, ShortStr


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def analyze(
    symbol: ShortStr,
    interval: Interval = "1d",
) -> dict[str, Any]:
    """Get technical analysis for a symbol.

    Auto-detects exchange. Returns composite rating plus detailed indicators.
    """
    return await scanner.analyze(symbol, interval)
