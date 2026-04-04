"""MCP tool: holistic 0-100 symbol scoring."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import Interval, validate_str


@mcp.tool()
async def score(
    symbol: str,
    interval: Interval = "1d",
) -> dict[str, Any]:
    """Get a holistic 0-100 score for a symbol.

    Combines technical rating (40%), momentum (25%), volume quality (15%),
    and trend strength (20%) into a single actionable score.
    """
    validate_str(symbol, "symbol")
    return await scanner.score(symbol, interval)
