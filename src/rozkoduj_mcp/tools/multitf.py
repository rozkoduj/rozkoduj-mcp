"""MCP tool: multi-timeframe analysis with alignment scoring."""

from collections import Counter
from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import ta as ta_service

Interval = Literal["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d", "1W", "1M"]

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

    analyses: list[dict[str, Any]] = []
    directions: list[str] = []

    for tf in tfs:
        data = await ta_service.get_analysis(symbol, "", "", tf)
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

    return {
        "symbol": data.get("symbol", symbol),
        "exchange": data.get("exchange", ""),
        "analysis": analyses,
        "alignment": {
            "direction": top_direction,
            "score": f"{top_count}/{len(tfs)}",
            "detail": dict(counts),
        },
    }
