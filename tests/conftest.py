"""Shared test fixtures for rozkoduj-mcp."""

import asyncio
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from rozkoduj_mcp import iam_client
from rozkoduj_mcp.services import scanner


@pytest.fixture(autouse=True)
def _scanner_semaphore() -> Iterator[None]:
    """Match the production lifespan contract.

    Without setup_client(), scanner._get_semaphore() correctly raises - we
    pre-init the semaphore here so individual tests that patch only
    ``scanner.client`` (the common case) keep working without each having
    to call setup_client themselves.
    """
    scanner._request_semaphore = asyncio.Semaphore(scanner._MAX_CONCURRENT_REQUESTS)
    try:
        yield
    finally:
        scanner._request_semaphore = None


@pytest.fixture(autouse=True)
def _stub_metadata_server() -> Iterator[None]:
    """Pretend the platform metadata server is unreachable.

    Tests run off-platform so a real fetch would DNS-fail after the httpx
    timeout and slow every test. Patching ``iam_client._fetch`` to return
    ``None`` exercises the local-dev fallback path without any network IO.
    """
    iam_client.reset_cache()
    with patch.object(iam_client, "_fetch", new=AsyncMock(return_value=None)):
        yield
    iam_client.reset_cache()


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
