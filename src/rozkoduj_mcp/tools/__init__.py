"""MCP tools package."""

from typing import Literal

from mcp.types import ToolAnnotations

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

MAX_STR_LEN = 100

# All rozkoduj tools are read-only queries against live market data.
TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def validate_str(value: str, name: str) -> str:
    """Validate string input length."""
    if len(value) > MAX_STR_LEN:
        msg = f"{name} must be at most {MAX_STR_LEN} characters"
        raise ValueError(msg)
    return value
