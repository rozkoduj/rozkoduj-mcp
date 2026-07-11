"""Async client for the rozkoduj data API.

Outbound calls authenticate with a service-identity token. End-user
identity extracted from the inbound MCP JWT is propagated through
separate identity headers; the caller's bearer is never forwarded
(MCP 2025-06-18 spec).
"""

import asyncio
import logging
import os
import re
from typing import Any

import httpx

from rozkoduj_mcp import iam_client
from rozkoduj_mcp.auth import (
    current_client_ip,
    current_user_id,
    current_user_scopes,
    current_user_tier,
)
from rozkoduj_mcp.logging import current_trace_header

# Managed by server / HTTP lifespan - created on startup, closed on shutdown.
client: httpx.AsyncClient | None = None

# Cap concurrent upstream requests per process so bursts of tool calls stay
# within a friendly window.
_MAX_CONCURRENT_REQUESTS = 4
_request_semaphore: asyncio.Semaphore | None = None

# Retry only on connection-level failures (DNS hiccup, dropped socket,
# read-before-headers). httpx does not retry on 4xx/5xx by design;
# those are deterministic and retrying just doubles latency.
_TRANSPORT_RETRIES = 2

logger = logging.getLogger(__name__)

# A Rozkoduj API key is ``rzk_`` followed by 40 hex chars (44 chars total).
_API_KEY_RE = re.compile(r"\Arzk_[0-9a-f]{40}\Z")


def _self_host_credential() -> str | None:
    """The configured self-host API key, when well-formed - else ``None``.

    Off-platform deployments authenticate to the data API with a
    Rozkoduj-issued ``rzk_`` key in ``ROZKODUJ_API_KEY``. A malformed value is
    treated as absent rather than sent as a bearer that would only be rejected; the
    malformed case is surfaced loudly once at startup (see
    :func:`log_self_host_status`), so the hot path stays quiet.
    """
    key = os.environ.get("ROZKODUJ_API_KEY")
    if key and _API_KEY_RE.match(key):
        return key
    return None


def log_self_host_status() -> None:
    """Log the outbound-auth posture once at startup, without the secret.

    Outbound mode is environment-determined: on Cloud Run the IAM
    service-identity token is used; off-platform a well-formed
    ``ROZKODUJ_API_KEY`` is the fallback. Logs which is configured (prefix
    only) so an operator can see why requests authenticate the way they do.
    """
    key = os.environ.get("ROZKODUJ_API_KEY")
    if not key:
        logger.info("outbound_auth: self-host key absent (IAM or anonymous)")
        return
    if _API_KEY_RE.match(key):
        logger.info("outbound_auth: self-host key configured (prefix=%s)", key[:12])
    else:
        logger.warning(
            "outbound_auth: self-host key malformed (expected rzk_ + 40 hex); ignoring"
        )


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
            if exc.response.status_code == 404:
                msg = f"{context} not found"
                raise RuntimeError(msg) from exc
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"Data backend unavailable for {context}"
            raise RuntimeError(msg) from exc
        return resp.json()


async def _outbound_headers() -> dict[str, str]:
    """Build the auth, identity, and trace headers for an outbound call."""
    headers: dict[str, str] = {}

    # Service-identity token when running on the platform; a configured API key
    # for self-hosted deployments off-platform. Platform identity takes
    # precedence.
    credential = await iam_client.get_id_token() or _self_host_credential()
    if credential:
        headers["Authorization"] = f"Bearer {credential}"

    user_id = current_user_id.get()
    if user_id:
        headers["X-User-Id"] = user_id
        tier = current_user_tier.get()
        if tier:
            headers["X-User-Tier"] = tier
        scopes = current_user_scopes.get()
        if scopes:
            headers["X-User-Scopes"] = scopes

    # Attach the captured end-client IP so anonymous callers are identified
    # individually on outbound calls, not collapsed onto this server.
    client_ip = current_client_ip.get()
    if client_ip:
        headers["X-Client-Ip"] = client_ip

    trace = current_trace_header.get()
    if trace:
        headers["X-Cloud-Trace-Context"] = trace

    return headers


async def list_strategies(
    *,
    status: str = "active",
    sort: str = "score_desc",
    visibility: str = "public",
    family: str | None = None,
    symbol: str | None = None,
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
    if symbol:
        params["symbol"] = symbol
    return await _get("/strategies", "list strategies", params=params)


async def strategy_details(identifier: str) -> dict[str, Any]:
    """Fetch single Rozkoduj strategy by slug or algorithm_uid."""
    return await _get(f"/strategies/{identifier}", f"strategy {identifier}")


async def search_research(
    query: str, locale: str | None = None, limit: int = 5
) -> dict[str, Any]:
    """One hybrid search over the research corpus; the knowledge layer joins
    server-side for entitled callers."""
    payload: dict[str, Any] = {"query": query, "limit": limit}
    if locale:
        payload["locale"] = locale
    return await _post("/research/search", "research", json=payload)


async def list_instruments(
    *,
    asset_class: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """The instrument catalog."""
    params: dict[str, str | int] = {"limit": limit, "offset": offset}
    if asset_class:
        params["asset_class"] = asset_class
    if status:
        params["status"] = status
    return await _get("/instruments", "list instruments", params=params)


async def instrument_details(symbol: str) -> dict[str, Any]:
    """One instrument's dossier by instrument id or bare ticker."""
    return await _get(f"/instruments/{symbol}", f"instrument {symbol}")
