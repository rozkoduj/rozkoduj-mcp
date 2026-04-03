"""MCP tool: community trading ideas with sentiment."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner


@mcp.tool()
async def ideas(
    symbol: str,
    sort: Literal["recent", "trending", "week_popular"] = "recent",
    limit: int = 10,
) -> dict[str, Any]:
    """Get community trading ideas for a symbol.

    Returns ideas with direction (long/short) and aggregate sentiment ratio.
    """
    limit = max(1, min(limit, 20))
    return await scanner.ideas(symbol, sort=sort, limit=limit)
