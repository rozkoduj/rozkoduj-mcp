"""Async client for the rozkoduj data API."""

from typing import Any

import httpx

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
        resp = await _get_client().post("/scan", json=payload)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for market {market!r}: {exc}"
        raise RuntimeError(msg) from exc

    data: Any = resp.json()
    return data.get("results", data) if isinstance(data, dict) else data


async def analyze(
    symbol: str,
    interval: str = "1d",
) -> dict[str, Any]:
    """Fetch technical analysis for a single symbol."""
    try:
        resp = await _get_client().post("/analyze", json={"symbol": symbol, "interval": interval})
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
            "/movers", json={"market": market, "direction": direction, "limit": limit}
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for movers {market}/{direction}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def score(
    symbol: str,
    interval: str = "1d",
) -> dict[str, Any]:
    """Get holistic 0-100 score for a symbol."""
    try:
        resp = await _get_client().post("/score", json={"symbol": symbol, "interval": interval})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for score {symbol}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def fundamentals(symbol: str) -> dict[str, Any]:
    """Fetch fundamental data for a symbol."""
    try:
        resp = await _get_client().post("/fundamentals", json={"symbol": symbol})
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for fundamentals {symbol}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def buzz(query: str, lang: str = "en", wiki_article: str | None = None) -> dict[str, Any]:
    """Get attention signal: news count + Wikipedia pageview trend."""
    try:
        params: dict[str, str | int] = {"query": query, "lang": lang}
        if wiki_article:
            params["wiki_article"] = wiki_article
        resp = await _get_client().get("/buzz", params=params)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for buzz {query}: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def market_pulse() -> dict[str, Any]:
    """Get market regime: stocks + crypto fear/greed + VIX."""
    try:
        resp = await _get_client().get("/market-pulse")
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for market-pulse: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]


async def calendar(days: int = 7, countries: str = "US", importance: int = 0) -> dict[str, Any]:
    """Fetch economic calendar events."""
    try:
        resp = await _get_client().get(
            "/calendar", params={"days": days, "countries": countries, "importance": importance}
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        msg = f"Data API error for calendar: {exc}"
        raise RuntimeError(msg) from exc

    return resp.json()  # type: ignore[no-any-return]
