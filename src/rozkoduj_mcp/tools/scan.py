"""MCP tool: market screening."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def scan(
    market: str = "crypto",
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    sort_by: str = "volume",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Screen global markets by any indicator, fundamental, or metric.

    Returns matching symbols with the requested columns.
    """
    validate_str(market, "market")
    validate_str(sort_by, "sort_by")
    limit = max(1, min(limit, 100))
    if filters and len(filters) > 20:
        msg = "filters must contain at most 20 entries"
        raise ValueError(msg)
    if columns and len(columns) > 50:
        msg = "columns must contain at most 50 entries"
        raise ValueError(msg)

    return await scanner.scan_market(
        market=market,
        filters=filters,
        columns=columns,
        sort_by=sort_by,
        order=order,
        limit=limit,
    )
