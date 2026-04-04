"""MCP tool: economic calendar."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import validate_str


@mcp.tool()
async def calendar(
    days: int = 7,
    countries: str = "US",
    importance: Literal[-1, 0, 1] = 0,
) -> dict[str, Any]:
    """Get upcoming economic calendar events.

    Filter by days ahead, countries (comma-separated codes), and
    importance level (-1=low, 0=medium, 1=high).
    """
    validate_str(countries, "countries")
    days = max(1, min(days, 30))
    return await scanner.calendar(days=days, countries=countries, importance=importance)
