"""MCP tool: multi-timeframe analysis with alignment scoring."""

import asyncio
from collections import Counter
from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service
from rozkoduj_mcp.tools import Interval

_DEFAULT_TIMEFRAMES: list[str] = ["15m", "1h", "4h", "1d", "1W"]


def _classify(recommendation: str) -> str:
    """Map recommendation to BUY / SELL / NEUTRAL."""
    if recommendation in ("BUY", "STRONG_BUY"):
        return "BUY"
    if recommendation in ("SELL", "STRONG_SELL"):
        return "SELL"
    return "NEUTRAL"


@mcp.tool()
async def multitf(
    symbol: str,
    timeframes: list[Interval] | None = None,
) -> dict[str, Any]:
    """Multi-timeframe analysis with alignment scoring.

    Default timeframes: 15m, 1h, 4h, 1d, 1W.
    """
    tfs = timeframes if timeframes else _DEFAULT_TIMEFRAMES

    all_data = await asyncio.gather(*(ta_service.get_analysis(symbol, "", "", tf) for tf in tfs))

    analyses: list[dict[str, Any]] = []
    directions: list[str] = []

    for tf, data in zip(tfs, all_data, strict=True):
        rec = data.get("summary", {}).get("recommendation", "NEUTRAL")
        direction = _classify(rec)
        directions.append(direction)

        analyses.append(
            {
                "timeframe": tf,
                "recommendation": rec,
                "direction": direction,
                "rsi": data.get("indicators", {}).get("RSI"),
                "macd": data.get("indicators", {}).get("MACD.macd"),
            }
        )

    counts = Counter(directions)
    top_direction, top_count = counts.most_common(1)[0]

    first = all_data[0]
    return {
        "symbol": first.get("symbol", symbol),
        "exchange": first.get("exchange", ""),
        "analysis": analyses,
        "alignment": {
            "direction": top_direction,
            "score": f"{top_count}/{len(tfs)}",
            "detail": dict(counts),
        },
    }
