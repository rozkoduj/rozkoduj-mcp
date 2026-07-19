"""Service identity for outbound calls to the data API.

Fetches a signed ID token from the platform metadata server with the data
API URL as audience, and uses it as the ``Authorization: Bearer`` value
on every outbound call. The metadata hop goes to a link-local address
that fast-fails when the process is not running on the platform.
"""

import asyncio
import logging
import os
import time
from typing import Final

import httpx

logger = logging.getLogger(__name__)

# Metadata-server endpoint that mints a fresh ID token for the default SA.
# Cloud Run / GCE intercepts requests to this hostname and serves them
# locally; outside Google's network the DNS lookup fails immediately.
_METADATA_URL: Final[str] = (
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
)
_METADATA_HEADERS: Final[dict[str, str]] = {"Metadata-Flavor": "Google"}
_FETCH_TIMEOUT_SECONDS: Final[float] = 3.0

# Refresh ~5 min before the 60-min Google-ID-token expiry to dodge races.
_CACHE_TTL_SECONDS: Final[float] = 3300.0

# Default audience matches what the data API expects to see in the token's
# ``aud`` claim. The API URL is the canonical Cloud Run service URL.
_DEFAULT_AUDIENCE: Final[str] = os.environ.get(
    "ROZKODUJ_API_AUDIENCE", "https://api.rozkoduj.com"
)

# Tokens carry the audience in their ``aud`` claim, so the cache is keyed
# by audience - a second audience must never be served another's token.
_cache: dict[str, tuple[str, float]] = {}
_lock = asyncio.Lock()


def _cached(audience: str, now: float) -> str | None:
    entry = _cache.get(audience)
    if entry and (now - entry[1]) < _CACHE_TTL_SECONDS:
        return entry[0]
    return None


async def get_id_token(audience: str = _DEFAULT_AUDIENCE) -> str | None:
    """Return a cached or freshly-minted Google ID token for ``audience``.

    Returns ``None`` when the metadata server is unreachable (local dev,
    tests, anything outside GCE / Cloud Run).
    """
    token = _cached(audience, time.monotonic())
    if token is not None:
        return token

    async with _lock:
        # Re-check after acquiring the lock so a burst of callers doesn't
        # stampede the metadata server.
        now = time.monotonic()
        token = _cached(audience, now)
        if token is not None:
            return token
        token = await _fetch(audience)
        if token is not None:
            _cache[audience] = (token, now)
        return token


async def _fetch(audience: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                _METADATA_URL,
                params={"audience": audience},
                headers=_METADATA_HEADERS,
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("metadata_id_token_unavailable", extra={"reason": repr(exc)})
        return None
    return resp.text.strip() or None


def reset_cache() -> None:
    """Clear all cached tokens. Internal helper, not part of the public API."""
    _cache.clear()
