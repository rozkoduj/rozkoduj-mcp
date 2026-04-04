"""MCP tools package."""

from typing import Literal

Interval = Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1W", "1M"]

MAX_STR_LEN = 100


def validate_str(value: str, name: str) -> str:
    """Validate string input length."""
    if len(value) > MAX_STR_LEN:
        msg = f"{name} must be at most {MAX_STR_LEN} characters"
        raise ValueError(msg)
    return value
