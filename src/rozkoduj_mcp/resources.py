"""MCP resources: reference data for AI context."""

import json
from typing import get_args

from rozkoduj_mcp.server import mcp
from rozkoduj_mcp.tools import Market

# Display names keyed by Market literal. KeyError at import time if a Market
# id is added to the Literal without a matching display name here.
_MARKET_NAMES: dict[Market, str] = {
    "us": "US stocks (NYSE, NASDAQ, AMEX)",
    "uk": "UK stocks (LSE)",
    "germany": "German stocks (XETR, FWB)",
    "france": "French stocks (Euronext Paris)",
    "spain": "Spanish stocks (BME)",
    "italy": "Italian stocks (MIL)",
    "poland": "Polish stocks (GPW)",
    "turkey": "Turkish stocks (BIST)",
    "india": "Indian stocks (BSE, NSE)",
    "japan": "Japanese stocks (TSE)",
    "australia": "Australian stocks (ASX)",
    "brazil": "Brazilian stocks (B3)",
    "canada": "Canadian stocks (TSX)",
    "hongkong": "Hong Kong stocks (HKEX)",
    "korea": "Korean stocks (KRX)",
    "china": "Chinese stocks (SSE, SZSE)",
    "taiwan": "Taiwanese stocks (TWSE)",
    "indonesia": "Indonesian stocks (IDX)",
    "malaysia": "Malaysian stocks (Bursa)",
    "crypto": "Cryptocurrency (all exchanges)",
    "forex": "Forex pairs",
}

_MARKETS: list[dict[str, str]] = [{"id": m, "name": _MARKET_NAMES[m]} for m in get_args(Market)]

# Most useful screening columns.
_FIELDS: list[dict[str, str]] = [
    {"id": "close", "name": "Price", "category": "price"},
    {"id": "change", "name": "Change %", "category": "price"},
    {"id": "volume", "name": "Volume", "category": "price"},
    {"id": "market_cap", "name": "Market cap", "category": "price"},
    {"id": "relative_volume", "name": "Relative volume (10d)", "category": "volume"},
    {"id": "RSI", "name": "RSI (14)", "category": "technical"},
    {"id": "macd", "name": "MACD line", "category": "technical"},
    {"id": "macd_signal", "name": "MACD signal", "category": "technical"},
    {"id": "ADX", "name": "ADX (14)", "category": "technical"},
    {"id": "EMA20", "name": "EMA 20", "category": "moving_average"},
    {"id": "EMA50", "name": "EMA 50", "category": "moving_average"},
    {"id": "EMA200", "name": "EMA 200", "category": "moving_average"},
    {"id": "SMA20", "name": "SMA 20", "category": "moving_average"},
    {"id": "SMA50", "name": "SMA 50", "category": "moving_average"},
    {"id": "SMA200", "name": "SMA 200", "category": "moving_average"},
    {"id": "bb_upper", "name": "Bollinger upper", "category": "technical"},
    {"id": "bb_lower", "name": "Bollinger lower", "category": "technical"},
    {"id": "stoch_k", "name": "Stochastic %K", "category": "technical"},
    {"id": "CCI20", "name": "CCI (20)", "category": "technical"},
    {"id": "rating", "name": "Technical rating (-1 to 1)", "category": "rating"},
    {"id": "perf_week", "name": "Performance week %", "category": "performance"},
    {"id": "perf_1m", "name": "Performance month %", "category": "performance"},
    {"id": "perf_3m", "name": "Performance 3 months %", "category": "performance"},
    {"id": "perf_year", "name": "Performance year %", "category": "performance"},
    {"id": "pe_ttm", "name": "P/E ratio (TTM)", "category": "fundamental"},
    {"id": "pb", "name": "Price/Book", "category": "fundamental"},
    {"id": "ps", "name": "Price/Sales", "category": "fundamental"},
    {"id": "ev_ebitda", "name": "EV/EBITDA", "category": "fundamental"},
    {"id": "piotroski", "name": "Piotroski F-Score (0-9)", "category": "fundamental"},
    {"id": "altman_z", "name": "Altman Z-Score", "category": "fundamental"},
    {"id": "roe", "name": "ROE", "category": "fundamental"},
    {"id": "div_yield", "name": "Dividend yield", "category": "fundamental"},
    {"id": "payout_ratio", "name": "Payout ratio", "category": "fundamental"},
    {"id": "eps_growth_yoy", "name": "EPS growth YoY", "category": "fundamental"},
    {"id": "sector", "name": "Sector", "category": "classification"},
    {"id": "industry", "name": "Industry", "category": "classification"},
]

# Data freshness contract - documented for AI agents reading rozkoduj://freshness-contract.
_FRESHNESS_CONTRACT: dict[str, object] = {
    "version": 1,
    "summary": (
        "Every tool response carries data_date, freshness, staleness_seconds, and "
        "fetched_at so agents can reason about how stale the underlying data is "
        "before acting on it."
    ),
    "fields": [
        {
            "name": "data_date",
            "type": "string | null",
            "format": "YYYY-MM-DD",
            "description": (
                "Source date of the underlying market data. Null when the data does "
                "not have a discrete snapshot date (e.g. a malformed upstream row)."
            ),
        },
        {
            "name": "freshness",
            "type": "string",
            "values": ["LIVE", "RECENT", "STALE", "UNKNOWN"],
            "description": (
                "Categorical bucket for data_date. LIVE = today (<= 1 day). "
                "RECENT = within 5 days (covers weekends and holidays). "
                "STALE = older than 5 days. UNKNOWN = data_date is null or invalid."
            ),
        },
        {
            "name": "staleness_seconds",
            "type": "integer | null",
            "description": (
                "Seconds elapsed since UTC midnight of data_date. Null when "
                "data_date is unknown. Use this for numeric reasoning instead of "
                "parsing the freshness string."
            ),
        },
        {
            "name": "fetched_at",
            "type": "string",
            "format": "ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)",
            "description": (
                "Timestamp when the API generated this response. Distinct from "
                "data_date - useful for cache invalidation and request tracing."
            ),
        },
    ],
    "list_endpoints": (
        "Tools that return a list (scan) carry data_date and freshness on each "
        "item rather than at the top level."
    ),
    "guidance_for_agents": (
        "If freshness is STALE or UNKNOWN, surface that to the user before "
        "presenting numbers as current. Prefer LIVE data when multiple sources "
        "are available."
    ),
}


# Filter operators for scan tool.
_OPERATORS: list[dict[str, str]] = [
    {"id": "greater", "name": "Greater than", "example": "RSI > 70"},
    {"id": "less", "name": "Less than", "example": "RSI < 30"},
    {"id": "equal", "name": "Equal to", "example": "sector = 'Technology'"},
    {"id": "not_equal", "name": "Not equal to", "example": "sector != 'Utilities'"},
    {"id": "in_range", "name": "Between two values", "example": "P/E between [5, 15]"},
    {"id": "not_in_range", "name": "Outside range", "example": "P/E not in [5, 15]"},
    {"id": "crosses_above", "name": "Crosses above", "example": "macd crosses above macd_signal"},
    {"id": "crosses_below", "name": "Crosses below", "example": "macd crosses below macd_signal"},
    {"id": "above_pct", "name": "Above by %", "example": "close above SMA200 by 5%"},
    {"id": "below_pct", "name": "Below by %", "example": "close below SMA200 by 5%"},
]


_MARKETS_JSON = json.dumps(_MARKETS, indent=2)
_FIELDS_JSON = json.dumps(_FIELDS, indent=2)
_OPERATORS_JSON = json.dumps(_OPERATORS, indent=2)
_FRESHNESS_CONTRACT_JSON = json.dumps(_FRESHNESS_CONTRACT, indent=2)


@mcp.resource("rozkoduj://markets", name="Available markets", mime_type="application/json")
def get_markets() -> str:
    """List of markets available for screening with the scan tool."""
    return _MARKETS_JSON


@mcp.resource("rozkoduj://fields", name="Screening fields", mime_type="application/json")
def get_fields() -> str:
    """Popular screening fields for use with scan tool columns and filters."""
    return _FIELDS_JSON


@mcp.resource("rozkoduj://operators", name="Filter operators", mime_type="application/json")
def get_operators() -> str:
    """Filter operators for use with scan tool filters."""
    return _OPERATORS_JSON


@mcp.resource(
    "rozkoduj://freshness-contract",
    name="Data freshness contract",
    mime_type="application/json",
)
def get_freshness_contract() -> str:
    """Schema contract for the data_date / freshness / staleness_seconds / fetched_at fields."""
    return _FRESHNESS_CONTRACT_JSON
