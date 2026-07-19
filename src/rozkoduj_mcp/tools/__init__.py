"""MCP tools package."""

from typing import Annotated

from mcp.types import ToolAnnotations
from pydantic import Field

# Reusable bounded string parameter types. The length limits land in the
# generated tool JSON Schema and FastMCP/Pydantic enforce them before the
# tool body runs - so the calling LLM sees the bound and self-limits.
SearchQuery = Annotated[str, Field(min_length=2, max_length=300)]

# Ticker charset: dots, carets, dashes and equals cover BRK.B-style symbols
# plus index/FX notations. No wildcards, no separators. The first character
# must be alphanumeric or a caret so a symbol can never be a pure dot
# sequence ("." / "..") - those are RFC 3986 dot-segments and would collapse
# the upstream request path the symbol is interpolated into.
Symbol = Annotated[
    str,
    Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9^][A-Za-z0-9.^=-]*$"),
]

# All rozkoduj tools are read-only queries against Rozkoduj's own bounded
# corpus (strategy catalog, research, knowledge base) - a closed domain, not the
# open web or third-party services, so openWorldHint is False. idempotentHint
# is omitted deliberately: the spec defines it as meaningful only when
# readOnlyHint is False.
TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=False,
)
