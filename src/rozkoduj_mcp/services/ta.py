"""Technical analysis service — delegates to rozkoduj data API."""

from typing import Any

from rozkoduj_mcp.services import scanner


async def get_analysis(symbol: str, interval: str) -> dict[str, Any]:
    """Fetch TA for a single symbol via the data API."""
    return await scanner.analyze(symbol=symbol, interval=interval)
