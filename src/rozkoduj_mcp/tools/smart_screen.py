"""MCP tool: pre-built intelligent screens."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner

Preset = Literal["unusual_volume", "oversold_bounce", "breakout", "momentum", "dividend"]

_PRESETS: dict[str, dict[str, Any]] = {
    "unusual_volume": {
        "filters": [
            {"left": "relative_volume_10d_calc", "operation": "greater", "right": 2.0},
            {"left": "Recommend.All", "operation": "greater", "right": 0.1},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "volume",
            "relative_volume_10d_calc",
            "Recommend.All",
        ],
        "sort_by": "relative_volume_10d_calc",
    },
    "oversold_bounce": {
        "filters": [
            {"left": "RSI", "operation": "less", "right": 30},
            {"left": "MACD.macd", "operation": "crosses_above", "right": "MACD.signal"},
        ],
        "columns": ["name", "close", "change", "RSI", "MACD.macd", "MACD.signal"],
        "sort_by": "RSI",
        "order": "asc",
    },
    "breakout": {
        "filters": [
            {"left": "ADX", "operation": "greater", "right": 25},
            {"left": "relative_volume_10d_calc", "operation": "greater", "right": 1.5},
            {"left": "Recommend.All", "operation": "greater", "right": 0.3},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "ADX",
            "relative_volume_10d_calc",
            "Perf.W",
            "Recommend.All",
        ],
        "sort_by": "change",
    },
    "momentum": {
        "filters": [
            {"left": "Perf.1M", "operation": "greater", "right": 10},
            {"left": "EMA20", "operation": "greater", "right": "EMA50"},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "Perf.1M",
            "Perf.3M",
            "EMA20",
            "EMA50",
            "RSI",
        ],
        "sort_by": "Perf.1M",
    },
    "dividend": {
        "filters": [
            {"left": "dividend_yield_recent", "operation": "greater", "right": 0.03},
            {"left": "dividend_payout_ratio_ttm", "operation": "less", "right": 0.6},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "dividend_yield_recent",
            "dividend_payout_ratio_ttm",
            "Perf.Y",
        ],
        "sort_by": "dividend_yield_recent",
    },
}


@mcp.tool()
async def smart_screen(
    preset: Preset,
    market: str = "america",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Run a pre-built intelligent screen.

    Presets: unusual_volume, oversold_bounce, breakout, momentum, dividend.
    """
    limit = max(1, min(limit, 50))
    config = _PRESETS[preset]

    return await scanner.scan_market(
        market=market,
        filters=config["filters"],
        columns=config["columns"],
        sort_by=config.get("sort_by", "volume"),
        order=config.get("order", "desc"),
        limit=limit,
    )
