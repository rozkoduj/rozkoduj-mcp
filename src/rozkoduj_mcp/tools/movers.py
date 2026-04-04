"""MCP tool: top gainers and losers."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import validate_str


@mcp.tool()
async def movers(
    market: str = "crypto",
    direction: Literal["gainers", "losers", "both"] = "gainers",
    limit: int = 10,
) -> dict[str, Any]:
    """Top gainers/losers. Filters out low-volume and junk tickers automatically."""
    validate_str(market, "market")
    limit = max(1, min(limit, 50))

    return await scanner.movers(market=market, direction=direction, limit=limit)
