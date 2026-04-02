"""Technical analysis service — delegates to rozkoduj data API."""

from typing import Any

from rozkoduj_mcp.services import scanner


async def get_analysis(symbol: str, exchange: str, screener: str, interval: str) -> dict[str, Any]:
    """Fetch TA for a single symbol via the data API."""
    query_symbol = f"{exchange}:{symbol}" if exchange and ":" not in symbol else symbol

    return await scanner.analyze(symbol=query_symbol, interval=interval)
