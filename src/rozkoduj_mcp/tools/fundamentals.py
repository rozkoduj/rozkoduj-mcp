"""MCP tool: fundamental data, analyst consensus, earnings."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import validate_str


@mcp.tool()
async def fundamentals(symbol: str) -> dict[str, Any]:
    """Get fundamental data for a symbol.

    Returns valuation (P/E, P/B, Piotroski), analyst consensus (buy/hold/sell
    counts, price targets), upcoming earnings, and dividend info.
    """
    validate_str(symbol, "symbol")
    return await scanner.fundamentals(symbol)
