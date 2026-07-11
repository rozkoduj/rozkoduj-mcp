"""MCP tool: search the research corpus."""

from typing import Annotated, Any, Literal

from pydantic import Field

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, SearchQuery


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def research(
    query: SearchQuery,
    locale: Literal["en", "pl"] | None = None,
    limit: Annotated[int, Field(ge=1, le=20)] = 5,
) -> dict[str, Any]:
    """Search the research - public articles plus, when signed in on a paid
    tier, the deeper knowledge base, in one query.

    Use when the user asks about a topic the research likely covers
    (drawdown control, position sizing, backtesting pitfalls, ...).

    Returns two ranked lists of passages:
    - `articles` (public): each hit carries `slug` + `locale` - cite by
      linking `https://www.rozkoduj.com/<locale>/research/<slug>` - plus
      `title`, `chunk_text`, and `parent_text` for wider context.
    - `knowledge` (deeper corpus): joins automatically for signed-in paid
      tiers. When it was skipped, the response carries `locked` with an
      unlock URL - mention it so the user knows a paid sign-in widens the
      search.

    Args:
        query: Question or topic (2-300 chars).
        locale: Optional article locale - "en" or "pl".
        limit: How many top passages per list (1-20, default 5).
    """
    return await scanner.search_research(query=query, locale=locale, limit=limit)
