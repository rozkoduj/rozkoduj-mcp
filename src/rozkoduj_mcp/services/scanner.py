"""Async client for the rozkoduj data API."""

import asyncio
from typing import Any

import httpx

# Managed by server / HTTP lifespan - created on startup, closed on shutdown.
client: httpx.AsyncClient | None = None

# Cap concurrent upstream requests per process. Tools that fan out (compare,
# multitf, decode) used to hammer the backend in lockstep and trip rate limits;
# the semaphore keeps each MCP request within a friendly burst window.
_MAX_CONCURRENT_REQUESTS = 4
_request_semaphore: asyncio.Semaphore | None = None


def setup_client(api_url: str, timeout: float = 20.0) -> httpx.AsyncClient:
    """Create the module-level httpx client. Called from each transport's lifespan."""
    global client, _request_semaphore
    client = httpx.AsyncClient(base_url=api_url, timeout=timeout)
    _request_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
    return client


async def close_client() -> None:
    """Close the module-level httpx client. Idempotent."""
    global client, _request_semaphore
    if client is not None:
        await client.aclose()
        client = None
    _request_semaphore = None


def _get_client() -> httpx.AsyncClient:
    if client is None:
        msg = "scanner.client not initialized - server lifespan not started"
        raise RuntimeError(msg)
    return client


def _get_semaphore() -> asyncio.Semaphore:
    """Return the concurrency semaphore, lazily creating it if needed.

    setup_client() pre-creates the semaphore for production lifespans; lazy
    creation here keeps unit tests that patch only `client` working without
    forcing every test to call setup_client.
    """
    global _request_semaphore
    if _request_semaphore is None:
        _request_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)
    return _request_semaphore


async def _post(path: str, context: str, **kwargs: Any) -> Any:
    """POST to the data API with unified error handling."""
    async with _get_semaphore():
        try:
            resp = await _get_client().post(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        return resp.json()


async def _get(path: str, context: str, **kwargs: Any) -> Any:
    """GET from the data API with unified error handling."""
    async with _get_semaphore():
        try:
            resp = await _get_client().get(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        return resp.json()


async def scan_market(
    market: str,
    columns: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Screen a market. Returns one dict per matched ticker."""
    return await _post(  # type: ignore[no-any-return]
        "/scan",
        f"market {market!r}",
        json={
            "market": market,
            "columns": columns,
            "filters": filters,
            "sort_by": sort_by,
            "order": order,
            "limit": limit,
        },
    )


async def analyze(symbol: str, interval: str = "1d") -> dict[str, Any]:
    """Fetch technical analysis for a single symbol."""
    return await _post("/analyze", symbol, json={"symbol": symbol, "interval": interval})  # type: ignore[no-any-return]


async def movers(
    market: str = "crypto", direction: str = "gainers", limit: int = 10
) -> dict[str, Any]:
    """Top gainers/losers."""
    return await _post(  # type: ignore[no-any-return]
        "/movers",
        f"movers {market}/{direction}",
        json={"market": market, "direction": direction, "limit": limit},
    )


async def score(symbol: str, interval: str = "1d") -> dict[str, Any]:
    """Get holistic 0-100 score for a symbol."""
    return await _post("/score", f"score {symbol}", json={"symbol": symbol, "interval": interval})  # type: ignore[no-any-return]


async def fundamentals(symbol: str) -> dict[str, Any]:
    """Fetch fundamental data for a symbol."""
    return await _post("/fundamentals", f"fundamentals {symbol}", json={"symbol": symbol})  # type: ignore[no-any-return]


async def buzz(query: str, lang: str = "en", wiki_article: str | None = None) -> dict[str, Any]:
    """Get attention signal: news count + Wikipedia pageview trend."""
    params: dict[str, str | int] = {"query": query, "lang": lang}
    if wiki_article:
        params["wiki_article"] = wiki_article
    return await _get("/buzz", f"buzz {query}", params=params)  # type: ignore[no-any-return]


async def market_pulse() -> dict[str, Any]:
    """Get market regime: stocks + crypto fear/greed + VIX."""
    return await _get("/market-pulse", "market-pulse")  # type: ignore[no-any-return]


async def calendar(days: int = 7, countries: str = "US", importance: int = 0) -> dict[str, Any]:
    """Fetch economic calendar events."""
    return await _get(  # type: ignore[no-any-return]
        "/calendar",
        "calendar",
        params={"days": days, "countries": countries, "importance": importance},
    )


async def digest(market: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Scan markets for anomalies and return top gems ranked by surprise."""
    params: dict[str, str | int] = {"limit": limit}
    if market:
        params["market"] = market
    return await _get("/digest", f"digest {market or 'global'}", params=params)  # type: ignore[no-any-return]


async def decode(symbol: str, query: str = "", lang: str = "en") -> dict[str, Any]:
    """Full 3-dimensional decode: technical (multi-TF) + fundamental + sentiment."""
    params: dict[str, str] = {"symbol": symbol}
    if query:
        params["query"] = query
    if lang != "en":
        params["lang"] = lang
    return await _get("/decode", f"decode {symbol}", params=params)  # type: ignore[no-any-return]
