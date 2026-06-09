"""MCP tool: top gainers and losers."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Market


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def movers(
    market: Market = "crypto",
    direction: Literal["gainers", "losers", "both"] = "gainers",
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Top gainers/losers. Filters out low-volume and junk tickers automatically."""
    return await scanner.movers(market=market, direction=direction, limit=limit)
