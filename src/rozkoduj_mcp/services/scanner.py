"""Async client for the rozkoduj data API.

Outbound calls authenticate with a service-identity token. End-user
identity extracted from the inbound MCP JWT is propagated through
separate identity headers; the caller's bearer is never forwarded
(MCP 2025-06-18 spec).
"""

import asyncio
from typing import Any

import httpx

from rozkoduj_mcp import iam_client

# Managed by server / HTTP lifespan - created on startup, closed on shutdown.
client: httpx.AsyncClient | None = None

# Cap concurrent upstream requests per process so fan-out tools (compare,
# multitf, decode) stay within a friendly burst window.
_MAX_CONCURRENT_REQUESTS = 4
_request_semaphore: asyncio.Semaphore | None = None

# Retry only on connection-level failures (DNS hiccup, dropped socket,
# read-before-headers). httpx does not retry on 4xx/5xx by design;
# those are deterministic and retrying just doubles latency.
_TRANSPORT_RETRIES = 2


def setup_client(api_url: str, timeout: float = 20.0) -> httpx.AsyncClient:
    """Create the module-level httpx client. Called from each transport's lifespan."""
    global client, _request_semaphore
    client = httpx.AsyncClient(
        base_url=api_url,
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(retries=_TRANSPORT_RETRIES),
    )
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
    if _request_semaphore is None:
        msg = "scanner._request_semaphore not initialized - server lifespan not started"
        raise RuntimeError(msg)
    return _request_semaphore


def _rate_limit_error(context: str, exc: httpx.HTTPStatusError) -> RuntimeError:
    """Build a RuntimeError for an upstream 429 with the Retry-After hint."""
    retry_after = exc.response.headers.get("Retry-After", "later")
    msg = (
        f"Rate limit exceeded for {context}. Retry after {retry_after} "
        "seconds, or sign in to keep going."
    )
    return RuntimeError(msg)


async def _post(path: str, context: str, **kwargs: Any) -> Any:
    """POST to the data API with auto-attached IAM auth + user headers."""
    extra = kwargs.pop("headers", None) or {}
    kwargs["headers"] = {**(await _outbound_headers()), **extra}
    async with _get_semaphore():
        try:
            resp = await _get_client().post(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise _rate_limit_error(context, exc) from exc
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        return resp.json()


async def _get(path: str, context: str, **kwargs: Any) -> Any:
    """GET from the data API with auto-attached IAM auth + user headers."""
    extra = kwargs.pop("headers", None) or {}
    kwargs["headers"] = {**(await _outbound_headers()), **extra}
    async with _get_semaphore():
        try:
            resp = await _get_client().get(path, **kwargs)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise _rate_limit_error(context, exc) from exc
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        return resp.json()


async def _outbound_headers() -> dict[str, str]:
    """Build the auth, identity, and trace headers for an outbound call."""
    from rozkoduj_mcp.auth import (
        current_user_id,
        current_user_scopes,
        current_user_tier,
    )
    from rozkoduj_mcp.logging import current_trace_header

    headers: dict[str, str] = {}

    id_token = await iam_client.get_id_token()
    if id_token is not None:
        headers["Authorization"] = f"Bearer {id_token}"

    user_id = current_user_id.get()
    if user_id:
        headers["X-User-Id"] = user_id
        tier = current_user_tier.get()
        if tier:
            headers["X-User-Tier"] = tier
        scopes = current_user_scopes.get()
        if scopes:
            headers["X-User-Scopes"] = scopes

    trace = current_trace_header.get()
    if trace:
        headers["X-Cloud-Trace-Context"] = trace

    return headers


async def scan_market(
    market: str,
    columns: list[str] | None = None,
    filters: list[dict[str, Any]] | None = None,
    sort_by: str = "volume",
    order: str = "desc",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Screen a market. Returns one dict per matched ticker."""
    return await _post(
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
    return await _post(
        "/analyze", symbol, json={"symbol": symbol, "interval": interval}
    )


async def movers(
    market: str = "crypto", direction: str = "gainers", limit: int = 10
) -> dict[str, Any]:
    """Top gainers/losers."""
    return await _post(
        "/movers",
        f"movers {market}/{direction}",
        json={"market": market, "direction": direction, "limit": limit},
    )


async def score(symbol: str, interval: str = "1d") -> dict[str, Any]:
    """Get holistic 0-100 score for a symbol."""
    return await _post(
        "/score", f"score {symbol}", json={"symbol": symbol, "interval": interval}
    )


async def fundamentals(symbol: str) -> dict[str, Any]:
    """Fetch fundamental data for a symbol."""
    return await _post(
        "/fundamentals", f"fundamentals {symbol}", json={"symbol": symbol}
    )


async def buzz(
    query: str, lang: str = "en", wiki_article: str | None = None
) -> dict[str, Any]:
    """Get attention signal: news count + optional pageview trend."""
    params: dict[str, str | int] = {"query": query, "lang": lang}
    if wiki_article:
        params["wiki_article"] = wiki_article
    return await _get("/buzz", f"buzz {query}", params=params)


async def market_pulse() -> dict[str, Any]:
    """Get market regime: stocks + crypto fear/greed + VIX."""
    return await _get("/market-pulse", "market-pulse")


async def calendar(
    days: int = 7, countries: str = "US", importance: int = 0
) -> dict[str, Any]:
    """Fetch economic calendar events."""
    return await _get(
        "/calendar",
        "calendar",
        params={"days": days, "countries": countries, "importance": importance},
    )


async def digest(market: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Scan markets for anomalies and return top gems ranked by surprise."""
    params: dict[str, str | int] = {"limit": limit}
    if market:
        params["market"] = market
    return await _get("/digest", f"digest {market or 'global'}", params=params)


async def decode(symbol: str, query: str = "", lang: str = "en") -> dict[str, Any]:
    """Full 3-dimensional decode: technical (multi-TF) + fundamental + sentiment."""
    params: dict[str, str] = {"symbol": symbol}
    if query:
        params["query"] = query
    if lang != "en":
        params["lang"] = lang
    return await _get("/decode", f"decode {symbol}", params=params)


async def list_strategies(
    *,
    status: str = "active",
    sort: str = "sharpe_desc",
    visibility: str = "public",
    family: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List Rozkoduj's published strategies."""
    params: dict[str, str | int] = {
        "status": status,
        "sort": sort,
        "visibility": visibility,
        "limit": limit,
        "offset": offset,
    }
    if family:
        params["family"] = family
    return await _get("/strategies", "list strategies", params=params)


async def strategy_details(identifier: str) -> dict[str, Any]:
    """Fetch single Rozkoduj strategy by slug or algorithm_uid."""
    return await _get(f"/strategies/{identifier}", f"strategy {identifier}")


async def search_articles(
    query: str, locale: str | None = None, limit: int = 5
) -> dict[str, Any]:
    """Hybrid search over Rozkoduj blog articles."""
    payload: dict[str, Any] = {"query": query, "limit": limit}
    if locale:
        payload["locale"] = locale
    return await _post("/articles/search", "search articles", json=payload)


async def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
    """Search Rozkoduj's extended knowledge base (auth-gated)."""
    return await _post(
        "/knowledge/search",
        "search knowledge",
        json={"query": query, "limit": limit},
    )
