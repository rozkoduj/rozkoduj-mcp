"""MCP tool: search over Rozkoduj blog articles."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def search_articles(
    query: str,
    locale: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Search Rozkoduj blog articles by keyword and meaning.

    Use when the user asks about a topic likely covered in a blog post.
    Returns ranked chunks with `slug` + `locale` so you can link the user
    to the full article at `https://www.rozkoduj.com/<locale>/blog/<slug>`.

    Each item carries:
    - `slug` + `locale` for citation/linking
    - `title` + `description` from the post frontmatter
    - `chunk_text` (the matched passage)
    - `parent_text` (the wider section the chunk came from - use for context)
    - `context_prefix` (contextual retrieval prefix; may be null)

    Args:
        query: User's question or topic (2-300 chars).
        locale: Optional ISO 639-1 language code (e.g. "en"). Omit to search all.
        limit: How many top chunks to return (1-20, default 5).
    """
    validate_str(query, "query")
    limit = max(1, min(limit, 20))
    return await scanner.search_articles(query=query, locale=locale, limit=limit)
