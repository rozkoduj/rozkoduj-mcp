"""MCP tool: market screening with 3000+ fields."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner


@mcp.tool()
async def scan(
    market: str = "crypto",
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    sort_by: str = "volume",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Screen markets with 3000+ fields.

    Returns matching symbols with the requested columns.
    """
    limit = max(1, min(limit, 100))

    return await scanner.scan_market(
        market=market,
        filters=filters,
        columns=columns,
        sort_by=sort_by,
        order=order,
        limit=limit,
    )
