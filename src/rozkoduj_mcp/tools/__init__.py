"""MCP tools package."""

from typing import Annotated, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

Interval = Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1W", "1M"]

Market = Literal[
    "us",
    "uk",
    "germany",
    "france",
    "spain",
    "italy",
    "poland",
    "turkey",
    "india",
    "japan",
    "australia",
    "brazil",
    "canada",
    "hongkong",
    "korea",
    "china",
    "taiwan",
    "indonesia",
    "malaysia",
    "crypto",
    "forex",
]

# Reusable bounded string parameter types. The length limits land in the
# generated tool JSON Schema and FastMCP/Pydantic enforce them before the
# tool body runs - so the calling LLM sees the bound and self-limits.
ShortStr = Annotated[str, Field(max_length=100)]
SearchQuery = Annotated[str, Field(min_length=2, max_length=300)]
# Short ISO 639-1 / BCP-47 language or locale codes (e.g. "en", "pt-BR").
LangCode = Annotated[str, Field(min_length=2, max_length=10)]

# All rozkoduj tools are read-only queries against live market data.
# idempotent: identical calls always return equivalent data so clients
# can safely retry on transient failures without confirmation.
TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=True,
)
