"""Async client for the rozkoduj data API."""

import os
from typing import Any

import httpx

_API_URL = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")
_TIMEOUT = 20.0

# Managed by server.py lifespan — created on startup, closed on shutdown.
client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    if client is None:
        msg = "scanner.client not initialized — server lifespan not started"
        raise RuntimeError(msg)
    return client


async def scan_market(
    market: str,
    columns: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Screen a market. Returns one dict per matched ticker."""
    payload: dict[str, Any] = {
        "market": market,
        "columns": columns,
        "filters": filters,
        "sort_by": sort_by,
        "order": order,
        "limit": limit,
    }

    try:
        resp = await _get_client().post("/v1/scan", json=payload)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for market {market!r}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def analyze(
    symbol: str,
    interval: str = "1d",
) -> dict[str, Any]:
    """Fetch technical analysis for a single symbol."""
    try:
        resp = await _get_client().post(
            "/v1/analyze", json={"symbol": symbol, "interval": interval}
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for {symbol}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def movers(
    market: str = "crypto",
    direction: str = "gainers",
    limit: int = 10,
) -> dict[str, Any]:
    """Top gainers/losers."""
    try:
        resp = await _get_client().post(
            "/v1/movers", json={"market": market, "direction": direction, "limit": limit}
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for movers {market}/{direction}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]
