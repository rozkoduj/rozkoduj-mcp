"""MCP tool: compare TA across multiple symbols."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service

Interval = Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1W", "1M"]


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

    results: list[dict[str, Any]] = []

    for sym in symbols:
        data = await ta_service.get_analysis(sym, "", "", interval)
        indicators = data.get("indicators", {})

        results.append(
            {
                "symbol": data.get("symbol", sym),
                "exchange": data.get("exchange", ""),
                "recommendation": data.get("summary", {}).get("recommendation", "NEUTRAL"),
                "rsi": indicators.get("RSI"),
                "macd": indicators.get("MACD.macd"),
                "macd_signal": indicators.get("MACD.signal"),
                "adx": indicators.get("ADX"),
                "oscillators": data.get("oscillators", {}),
                "moving_averages": data.get("moving_averages", {}),
            }
        )

    return results
