"""MCP tool: market regime detection."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner


@mcp.tool()
async def market_pulse() -> dict[str, Any]:
    """Get current market regime — RISK-ON, RISK-OFF, or NEUTRAL.

    Combines CNN Fear & Greed Index (US stocks, 7 sub-indicators),
    Alternative.me Fear & Greed (crypto), and VIX into a single verdict.
    """
    return await scanner.market_pulse()
