"""Async client for the rozkoduj data API."""

import os
from typing import Any

import httpx

_API_URL = os.environ.get("ROZKODUJ_API_URL", "https://api.rozkoduj.com")
_TIMEOUT = 20.0


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
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{_API_URL}/v1/scan", json=payload, timeout=_TIMEOUT)
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
    payload: dict[str, Any] = {"symbol": symbol, "interval": interval}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{_API_URL}/v1/analyze", json=payload, timeout=_TIMEOUT)
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
    payload: dict[str, Any] = {"market": market, "direction": direction, "limit": limit}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{_API_URL}/v1/movers", json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for movers {market}/{direction}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]
