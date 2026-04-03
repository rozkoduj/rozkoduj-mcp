"""MCP tool: fundamental data, analyst consensus, earnings."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner


@mcp.tool()
async def fundamentals(symbol: str) -> dict[str, Any]:
    """Get fundamental data for a symbol.

    Returns valuation (P/E, P/B, Piotroski), analyst consensus (buy/hold/sell
    counts, price targets), upcoming earnings, and dividend info.
    """
    return await scanner.fundamentals(symbol)
