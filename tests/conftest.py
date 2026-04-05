"""Shared test fixtures for rozkoduj-mcp."""

from typing import Any


def mock_analysis(
    rec: str = "BUY",
    rsi: float = 42.3,
    macd: float = 0.5,
    macd_signal: float = 0.3,
    adx: float = 25.1,
) -> dict[str, Any]:
    """Create a mock analysis response matching the data API format."""
    return {
        "symbol": "BTCUSDT",
        "exchange": "BINANCE",
        "interval": "1d",
        "summary": {"recommendation": rec},
        "oscillators": {"recommendation": "BUY"},
        "moving_averages": {"recommendation": "STRONG_BUY"},
        "indicators": {
            "RSI": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "ADX": adx,
        },
    }
