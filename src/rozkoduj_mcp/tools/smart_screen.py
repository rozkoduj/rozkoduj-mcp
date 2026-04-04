"""MCP tool: pre-built intelligent screens."""

from typing import Any, Literal

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.services import scanner
from rozkoduj_mcp.tools import TOOL_ANNOTATIONS, validate_str

Preset = Literal[
    "unusual_volume", "oversold_bounce", "breakout", "momentum", "dividend", "value", "growth"
]

_CRYPTO_MARKETS: frozenset[str] = frozenset({"crypto", "forex"})

# Minimum quality filters added to every preset to exclude junk.
_STOCK_QUALITY: list[dict[str, Any]] = [
    {"left": "volume", "operation": "greater", "right": 100_000},
    {"left": "close", "operation": "greater", "right": 1},
    {"left": "is_primary", "operation": "equal", "right": True},
]
_CRYPTO_QUALITY: list[dict[str, Any]] = [
    {"left": "volume", "operation": "greater", "right": 1_000_000},
    {"left": "close", "operation": "greater", "right": 0.0001},
]

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
            {"left": "dividend_yield_recent", "operation": "in_range", "right": [0.03, 0.15]},
            {"left": "dividend_payout_ratio_ttm", "operation": "in_range", "right": [0.01, 0.6]},
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
    "value": {
        "filters": [
            {"left": "price_earnings_ttm", "operation": "in_range", "right": [0, 15]},
            {"left": "piotroski_f_score_ttm", "operation": "greater", "right": 6},
            {"left": "RSI", "operation": "less", "right": 70},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "price_earnings_ttm",
            "piotroski_f_score_ttm",
            "price_book_fq",
            "RSI",
            "Recommend.All",
        ],
        "sort_by": "piotroski_f_score_ttm",
    },
    "growth": {
        "filters": [
            {
                "left": "earnings_per_share_diluted_yoy_growth_ttm",
                "operation": "greater",
                "right": 20,
            },
            {"left": "EMA20", "operation": "greater", "right": "EMA50"},
            {"left": "relative_volume_10d_calc", "operation": "greater", "right": 1.2},
        ],
        "columns": [
            "name",
            "close",
            "change",
            "earnings_per_share_diluted_yoy_growth_ttm",
            "Perf.1M",
            "relative_volume_10d_calc",
            "EMA20",
            "EMA50",
        ],
        "sort_by": "earnings_per_share_diluted_yoy_growth_ttm",
    },
}


@mcp.tool(annotations=TOOL_ANNOTATIONS)
async def smart_screen(
    preset: Preset,
    market: str = "america",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Run a pre-built intelligent screen.

    Presets: unusual_volume, oversold_bounce, breakout, momentum, dividend, value, growth.
    Value and growth combine fundamental data with technical analysis.
    """
    validate_str(market, "market")
    limit = max(1, min(limit, 50))
    config = _PRESETS[preset]

    quality = _CRYPTO_QUALITY if market in _CRYPTO_MARKETS else _STOCK_QUALITY
    filters = [*quality, *config["filters"]]

    return await scanner.scan_market(
        market=market,
        filters=filters,
        columns=config["columns"],
        sort_by=config.get("sort_by", "volume"),
        order=config.get("order", "desc"),
        limit=limit,
    )
