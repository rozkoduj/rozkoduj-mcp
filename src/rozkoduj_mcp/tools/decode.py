"""MCP tool: full 3-dimensional symbol decode."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def decode(
    symbol: str,
    query: str = "",
    lang: str = "en",
) -> dict[str, Any]:
    """Decode a symbol - full 3-dimensional analysis across multiple timeframes.

    Returns technical scores (daily, 4h, weekly), fundamental valuation
    and analyst data, and news sentiment. Each dimension scored 0-100.

    Use query param for better news search (e.g. "Siemens Healthineers").
    Use lang="pl" for Polish news context.
    """
    validate_str(symbol, "symbol")
    if query:
        validate_str(query, "query")
    return await scanner.decode(symbol=symbol, query=query, lang=lang)
