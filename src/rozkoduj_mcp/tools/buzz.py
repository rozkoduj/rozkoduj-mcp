"""MCP tool: per-ticker attention signal."""

from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, LangCode, ShortStr


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def buzz(
    query: ShortStr,
    lang: LangCode = "en",
    wiki_article: ShortStr | None = None,
) -> dict[str, Any]:
    """Get attention signal for any ticker or topic - globally, in any language.

    Uses headline count to gauge attention level (HIGH, MEDIUM, or LOW).
    Set lang='pl' for Polish news, lang='fr' for French, etc.
    Optionally pass wiki_article (e.g. 'Bitcoin', 'CD_Projekt') for pageview spike data.
    """
    return await scanner.buzz(query, lang=lang, wiki_article=wiki_article)
