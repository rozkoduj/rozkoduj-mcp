"""MCP tool: read-only hybrid search over Rozkoduj's private knowledge base.

Available when ``INTERNAL_API_KEY`` is configured. Read-only by design - no
write tool is exposed via MCP.
"""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
    """Search Rozkoduj's private knowledge base (auth-gated, read-only).

    Use when the user's question may be answered by Rozkoduj's curated
    internal notes that are not on the public site.

    Args:
        query: Question or topic (2-300 chars).
        limit: How many top chunks to return (1-20, default 5).
    """
    validate_str(query, "query")
    limit = max(1, min(limit, 20))
    return await scanner.search_knowledge(query=query, limit=limit)
