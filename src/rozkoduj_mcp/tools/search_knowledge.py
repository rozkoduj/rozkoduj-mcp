"""MCP tool: extended knowledge search (auth-gated, read-only)."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
    """Search Rozkoduj's extended knowledge base (auth-gated, read-only).

    Use when the user's question may be answered by Rozkoduj's curated content
    beyond what's on the public blog.

    Args:
        query: Question or topic (2-300 chars).
        limit: How many top chunks to return (1-20, default 5).
    """
    validate_str(query, "query")
    limit = max(1, min(limit, 20))
    return await scanner.search_knowledge(query=query, limit=limit)
