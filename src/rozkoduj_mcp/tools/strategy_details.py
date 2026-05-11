"""MCP tool: details for a single Rozkoduj trading strategy."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def strategy_details(identifier: str) -> dict[str, Any]:
    """Get full details for a single Rozkoduj strategy.

    `identifier` is either the URL slug (e.g. `ma-cross-ema`) or the
    `algorithm_uid` (ULID, e.g. `01J7...`). Returns a single strategy with
    its i18n names/descriptions, tags, family/variant/version metadata and
    the denormalized `best_run` blob (full metrics, sparkline, params_public,
    data range).

    Use this after `list_strategies` once a candidate is chosen, or when the
    user names a strategy directly. Returns 404 if not found.
    """
    validate_str(identifier, "identifier")
    return await scanner.strategy_details(identifier)
