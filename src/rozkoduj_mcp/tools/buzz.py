"""MCP tool: per-ticker attention signal."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def buzz(
    query: str,
    lang: str = "en",
    wiki_article: str | None = None,
) -> dict[str, Any]:
    """Get attention signal for any ticker or topic - globally, in any language.

    Uses headline count to gauge attention level (HIGH, MEDIUM, or LOW).
    Set lang='pl' for Polish news, lang='fr' for French, etc.
    Optionally pass wiki_article (e.g. 'Bitcoin', 'CD_Projekt') for pageview spike data.
    """
    validate_str(query, "query")
    validate_str(lang, "lang")
    if wiki_article:
        validate_str(wiki_article, "wiki_article")
    return await scanner.buzz(query, lang=lang, wiki_article=wiki_article)
