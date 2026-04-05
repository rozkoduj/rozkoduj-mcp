"""MCP tool: pre-built intelligent screens."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str

Preset = Literal[
    "unusual_volume", "oversold_bounce", "breakout", "momentum", "dividend", "value", "growth"
]

_PRESETS: dict[str, dict[str, Any]] = {
    "unusual_volume": {
        "filters": [
            {"left": "relative_volume", "operation": "greater", "right": 2.0},
            {"left": "rating", "operation": "greater", "right": 0.1},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "volume",
            "relative_volume",
            "rating",
        ],
        "sort_by": "relative_volume",
    },
    "oversold_bounce": {
        "filters": [
            {"left": "RSI", "operation": "less", "right": 30},
            {"left": "macd", "operation": "crosses_above", "right": "macd_signal"},
        ],
        "columns": ["name", "close", "change", "RSI", "macd", "macd_signal"],
        "sort_by": "RSI",
        "order": "asc",
    },
    "breakout": {
        "filters": [
            {"left": "ADX", "operation": "greater", "right": 25},
            {"left": "relative_volume", "operation": "greater", "right": 1.5},
            {"left": "rating", "operation": "greater", "right": 0.3},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "ADX",
            "relative_volume",
            "perf_week",
            "rating",
        ],
        "sort_by": "change",
    },
    "momentum": {
        "filters": [
            {"left": "perf_1m", "operation": "greater", "right": 10},
            {"left": "EMA20", "operation": "greater", "right": "EMA50"},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "perf_1m",
            "perf_3m",
            "EMA20",
            "EMA50",
            "RSI",
        ],
        "sort_by": "perf_1m",
    },
    "dividend": {
        "filters": [
            {"left": "div_yield", "operation": "in_range", "right": [0.03, 0.20]},
            {"left": "payout_ratio", "operation": "in_range", "right": [0.01, 0.80]},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "div_yield",
            "payout_ratio",
            "perf_year",
        ],
        "sort_by": "div_yield",
    },
    "value": {
        "filters": [
            {"left": "pe_ttm", "operation": "in_range", "right": [0, 15]},
            {"left": "piotroski", "operation": "greater", "right": 6},
            {"left": "RSI", "operation": "less", "right": 70},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "pe_ttm",
            "piotroski",
            "pb",
            "RSI",
            "rating",
        ],
        "sort_by": "piotroski",
    },
    "growth": {
        "filters": [
            {"left": "eps_growth_yoy", "operation": "greater", "right": 20},
            {"left": "EMA20", "operation": "greater", "right": "EMA50"},
            {"left": "relative_volume", "operation": "greater", "right": 1.2},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "eps_growth_yoy",
            "perf_1m",
            "relative_volume",
            "EMA20",
            "EMA50",
        ],
        "sort_by": "eps_growth_yoy",
    },
}


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def smart_screen(
    preset: Preset,
    market: str = "us",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Run a pre-built intelligent screen.

    Presets: unusual_volume, oversold_bounce, breakout, momentum, dividend, value, growth.
    Value and growth combine fundamental data with technical analysis.
    """
    validate_str(market, "market")
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
