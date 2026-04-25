"""MCP tool: multi-timeframe analysis with alignment scoring."""

import asyncio
from collections import Counter
from typing import Any

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, Interval, validate_str

_DEFAULT_TIMEFRAMES: list[str] = ["15m", "1h", "4h", "1d", "1W"]


def _classify(recommendation: str) -> str:
    """Map recommendation to BUY / SELL / NEUTRAL."""
    if recommendation in ("BUY", "STRONG_BUY"):
        return "BUY"
    if recommendation in ("SELL", "STRONG_SELL"):
        return "SELL"
    return "NEUTRAL"


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def multitf(
    symbol: str,
    timeframes: list[Interval] | None = None,
) -> dict[str, Any]:
    """Multi-timeframe analysis with alignment scoring.

    Default timeframes: 15m, 1h, 4h, 1d, 1W.
    """
    validate_str(symbol, "symbol")
    tfs = timeframes if timeframes else _DEFAULT_TIMEFRAMES
    if len(tfs) > 10:
        msg = "timeframes must contain at most 10 entries"
        raise ValueError(msg)

    raw = await asyncio.gather(
        *(scanner.analyze(symbol, tf) for tf in tfs),
        return_exceptions=True,
    )

    analyses: list[dict[str, Any]] = []
    directions: list[str] = []
    skipped: list[dict[str, str]] = []
    first_ok: dict[str, Any] | None = None

    for tf, data in zip(tfs, raw, strict=True):
        if isinstance(data, BaseException):
            skipped.append({"timeframe": tf, "reason": "upstream_unavailable"})
            continue
        if first_ok is None:
            first_ok = data
        rec = data.get("summary", {}).get("recommendation", "NEUTRAL")
        direction = _classify(rec)
        directions.append(direction)
        analyses.append(
            {
                "timeframe": tf,
                "recommendation": rec,
                "direction": direction,
                "rsi": data.get("indicators", {}).get("RSI"),
                "macd": data.get("indicators", {}).get("macd"),
            }
        )

    if not analyses:
        msg = f"No timeframe data available for {symbol}"
        raise RuntimeError(msg)

    counts = Counter(directions)
    top_direction, top_count = counts.most_common(1)[0]

    return {
        "symbol": (first_ok or {}).get("symbol", symbol),
        "exchange": (first_ok or {}).get("exchange", ""),
        "analysis": analyses,
        "alignment": {
            "direction": top_direction,
            "score": f"{top_count}/{len(analyses)}",
            "detail": dict(counts),
        },
        "skipped": skipped,
    }
