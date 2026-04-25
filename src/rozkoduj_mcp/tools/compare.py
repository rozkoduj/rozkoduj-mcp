"""MCP tool: compare TA across multiple symbols."""

import asyncio
from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Interval, validate_str


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def compare(
    symbols: list[str],
    interval: Interval = "1d",
) -> list[dict[str, Any]]:
    """Compare technical analysis across multiple symbols. Max 10."""
    if not symbols:
        msg = "symbols must contain at least 1 entry"
        raise ValueError(msg)
    if len(symbols) > 10:
        msg = "symbols must contain at most 10 entries"
        raise ValueError(msg)
    for sym in symbols:
        validate_str(sym, "symbol")

    raw = await asyncio.gather(
        *(scanner.analyze(sym, interval) for sym in symbols),
        return_exceptions=True,
    )

    rows: list[dict[str, Any]] = []
    for sym, data in zip(symbols, raw, strict=True):
        if isinstance(data, BaseException):
            rows.append(
                {
                    "symbol": sym,
                    "error": "upstream_unavailable",
                }
            )
            continue
        rows.append(
            {
                "symbol": data.get("symbol", sym),
                "exchange": data.get("exchange", ""),
                "recommendation": data.get("summary", {}).get("recommendation", "NEUTRAL"),
                "rsi": data.get("indicators", {}).get("RSI"),
                "macd": data.get("indicators", {}).get("macd"),
                "macd_signal": data.get("indicators", {}).get("macd_signal"),
                "adx": data.get("indicators", {}).get("ADX"),
                "oscillators": data.get("oscillators", {}),
                "moving_averages": data.get("moving_averages", {}),
            }
        )
    return rows
