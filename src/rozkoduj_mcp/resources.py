"""MCP resources: reference data for AI context."""

import json

from rozkoduj_mcp.server import mcp

# Markets available for screening via the scan tool.
_MARKETS: list[dict[str, str]] = [
    {"id": "america", "name": "US stocks (NYSE, NASDAQ, AMEX)"},
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
    {"id": "market_cap_basic", "name": "Market cap", "category": "price"},
    {"id": "relative_volume_10d_calc", "name": "Relative volume (10d)", "category": "volume"},
    {"id": "RSI", "name": "RSI (14)", "category": "technical"},
    {"id": "MACD.macd", "name": "MACD line", "category": "technical"},
    {"id": "MACD.signal", "name": "MACD signal", "category": "technical"},
    {"id": "ADX", "name": "ADX (14)", "category": "technical"},
    {"id": "EMA20", "name": "EMA 20", "category": "moving_average"},
    {"id": "EMA50", "name": "EMA 50", "category": "moving_average"},
    {"id": "EMA200", "name": "EMA 200", "category": "moving_average"},
    {"id": "SMA20", "name": "SMA 20", "category": "moving_average"},
    {"id": "SMA50", "name": "SMA 50", "category": "moving_average"},
    {"id": "SMA200", "name": "SMA 200", "category": "moving_average"},
    {"id": "BB.upper", "name": "Bollinger upper", "category": "technical"},
    {"id": "BB.lower", "name": "Bollinger lower", "category": "technical"},
    {"id": "Stoch.K", "name": "Stochastic %K", "category": "technical"},
    {"id": "CCI20", "name": "CCI (20)", "category": "technical"},
    {"id": "Recommend.All", "name": "Technical rating (-1 to 1)", "category": "rating"},
    {"id": "Perf.W", "name": "Performance week %", "category": "performance"},
    {"id": "Perf.1M", "name": "Performance month %", "category": "performance"},
    {"id": "Perf.3M", "name": "Performance 3 months %", "category": "performance"},
    {"id": "Perf.Y", "name": "Performance year %", "category": "performance"},
    {"id": "price_earnings_ttm", "name": "P/E ratio (TTM)", "category": "fundamental"},
    {"id": "price_book_fq", "name": "Price/Book", "category": "fundamental"},
    {"id": "price_sales_current", "name": "Price/Sales", "category": "fundamental"},
    {"id": "enterprise_value_ebitda_ttm", "name": "EV/EBITDA", "category": "fundamental"},
    {"id": "piotroski_f_score_ttm", "name": "Piotroski F-Score (0-9)", "category": "fundamental"},
    {"id": "altman_z_score_ttm", "name": "Altman Z-Score", "category": "fundamental"},
    {"id": "return_on_equity", "name": "ROE", "category": "fundamental"},
    {"id": "dividend_yield_recent", "name": "Dividend yield", "category": "fundamental"},
    {"id": "dividend_payout_ratio_ttm", "name": "Payout ratio", "category": "fundamental"},
    {
        "id": "earnings_per_share_diluted_yoy_growth_ttm",
        "name": "EPS growth YoY",
        "category": "fundamental",
    },
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
    {"id": "crosses_above", "name": "Crosses above", "example": "MACD crosses above signal"},
    {"id": "crosses_below", "name": "Crosses below", "example": "MACD crosses below signal"},
    {"id": "above%", "name": "Above by %", "example": "close above SMA200 by 5%"},
    {"id": "below%", "name": "Below by %", "example": "close below SMA200 by 5%"},
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
