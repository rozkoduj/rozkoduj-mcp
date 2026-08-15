"""MCP tools package."""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

# Reusable bounded string parameter types. The length limits land in the
# generated tool JSON Schema and the server/Pydantic enforce them before the
# tool body runs - so the calling LLM sees the bound and self-limits.
SearchQuery = Annotated[str, Field(min_length=2, max_length=300)]

# Instrument identifier charset. It admits exactly the two forms the data API
# resolves - a listing slug (`aapl-us`, `btc-usd`, `wig20-pl`) and a bare display
# ticker (`AAPL`, `BRK-B`) - and nothing else.
#
# Decorated forms - a dotted suffix, a leading caret, a trailing qualifier - are
# deliberately out. The API does not resolve them, so admitting them only bought a
# request that could never match, and the dot bought it at the price of RFC 3986
# dot-segments ("." / "..") in a path the symbol is interpolated into. Requiring an
# alphanumeric first character keeps that guarantee without needing the caret
# escape hatch.
#
# This pattern is part of the published wire contract: it lands in the tool JSON
# Schema, so changing it changes what every client validates against.
Symbol = Annotated[
    str,
    Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*$"),
]

# All rozkoduj tools are read-only queries against Rozkoduj's own bounded
# corpus (strategy catalog, research, knowledge base) - a closed domain, not the
# open web or third-party services, so openWorldHint is False. idempotentHint
# is omitted deliberately: the spec defines it as meaningful only when
# readOnlyHint is False.
# Field names are snake_case; the camelCase spelling the spec puts on the wire
# is the serialization alias, applied when the annotations are emitted.
TOOL_ANNOTATIONS = ToolAnnotations(
    read_only_hint=True,
    open_world_hint=False,
)
