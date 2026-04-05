"""MCP resources: reference data for AI context."""

import json

from rozkoduj_mcp.server import mcp

# Markets available for screening via the scan tool.
_MARKETS: list[dict[str, str]] = [
    {"id": "us", "name": "US stocks (NYSE, NASDAQ, AMEX)"},
    {"id": "uk", "name": "UK stocks (LSE)"},
    {"id": "germany", "name": "German stocks (XETR, FWB)"},
    {"id": "france", "name": "French stocks (Euronext Paris)"},
    {"id": "spain", "name": "Spanish stocks (BME)"},
    {"id": "italy", "name": "Italian stocks (MIL)"},
    {"id": "poland", "name": "Polish stocks (GPW)"},
    {"id": "turkey", "name": "Turkish stocks (BIST)"},
    {"id": "india", "name": "Indian stocks (BSE, NSE)"},
    {"id": "japan", "name": "Japanese stocks (TSE)"},
    {"id": "australia", "name": "Australian stocks (ASX)"},
    {"id": "brazil", "name": "Brazilian stocks (B3)"},
    {"id": "canada", "name": "Canadian stocks (TSX)"},
    {"id": "hongkong", "name": "Hong Kong stocks (HKEX)"},
    {"id": "korea", "name": "Korean stocks (KRX)"},
    {"id": "china", "name": "Chinese stocks (SSE, SZSE)"},
    {"id": "taiwan", "name": "Taiwanese stocks (TWSE)"},
    {"id": "indonesia", "name": "Indonesian stocks (IDX)"},
    {"id": "malaysia", "name": "Malaysian stocks (Bursa)"},
    {"id": "crypto", "name": "Cryptocurrency (all exchanges)"},
    {"id": "forex", "name": "Forex pairs"},
]

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
