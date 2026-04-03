"""MCP tool: compare TA across multiple symbols."""

import asyncio
from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service
from rozkoduj_mcp.tools import Interval


@mcp.tool()
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

    analyses = await asyncio.gather(
        *(ta_service.get_analysis(sym, interval) for sym in symbols)
    )

    return [
        {
            "symbol": data.get("symbol", sym),
            "exchange": data.get("exchange", ""),
            "recommendation": data.get("summary", {}).get("recommendation", "NEUTRAL"),
            "rsi": data.get("indicators", {}).get("RSI"),
            "macd": data.get("indicators", {}).get("MACD.macd"),
            "macd_signal": data.get("indicators", {}).get("MACD.signal"),
            "adx": data.get("indicators", {}).get("ADX"),
            "oscillators": data.get("oscillators", {}),
            "moving_averages": data.get("moving_averages", {}),
        }
        for sym, data in zip(symbols, analyses, strict=True)
    ]
