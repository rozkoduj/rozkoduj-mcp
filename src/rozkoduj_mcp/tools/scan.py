"""MCP tool: market screening."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Market, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def scan(
    market: Market = "crypto",
    filters: Annotated[
        list[dict[str, Any]] | None,
        Field(
            description=(
                "Filter clauses applied AND-style. Each entry is "
                "{'left': <field>, 'operation': <op>, 'right': <value>}. "
                "Example: [{'left': 'volume', 'operation': 'greater', 'right': 1000000}]."
            ),
        ),
    ] = None,
    columns: Annotated[
        list[str] | None,
        Field(
            description=(
                "Fields to return per row. Example: "
                "['name', 'close', 'volume', 'change', 'RSI', 'market_cap_basic']. "
                "Defaults to a sensible baseline when omitted."
            ),
        ),
    ] = None,
    sort_by: Annotated[
        str,
        Field(
            description="Column name used to order results (e.g. 'volume', 'change')."
        ),
    ] = "volume",
    order: Literal["asc", "desc"] = "desc",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Screen global markets by any indicator, fundamental, or metric.

    Returns matching symbols with the requested columns.
    """
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
