"""MCP tool: economic calendar."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, ShortStr


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def calendar(
    days: Annotated[int, Field(ge=1, le=30)] = 7,
    countries: ShortStr = "US",
    importance: Literal[-1, 0, 1] = 0,
) -> dict[str, Any]:
    """Get upcoming economic calendar events.

    Filter by days ahead (1-30), countries (comma-separated codes), and
    importance level (-1=low, 0=medium, 1=high).
    """
    return await scanner.calendar(days=days, countries=countries, importance=importance)
