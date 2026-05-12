"""Cloud Run service identity for outbound calls to the data API.

The MCP fetches a Google-signed ID token from the GCE metadata server with
the data API URL as audience. The API accepts that token, reads the ``email``
claim to confirm the caller is this MCP's service account, and then trusts
the end-user identity headers (``X-User-Id`` / ``X-User-Tier`` / ``X-User-Scopes``)
that ride alongside.

Tokens are valid for 60 minutes; we refresh proactively at 55 to dodge edge-
of-validity churn. The metadata-server hop is to a link-local address inside
Google's network (``169.254.169.254`` aliased as ``metadata.google.internal``)
— fast and reliable inside Cloud Run, hard-fails fast outside it.

We deliberately do not pull in ``google-auth``: the metadata-server endpoint
is a single ``httpx.GET`` with one custom header, and ``google-auth`` would
drag in the synchronous ``requests`` transport stack for no benefit.
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
_DEFAULT_AUDIENCE: Final[str] = os.environ.get("ROZKODUJ_API_AUDIENCE", "https://api.rozkoduj.com")

_cached_token: str | None = None
_cached_at: float = 0.0
_lock = asyncio.Lock()


async def get_id_token(audience: str = _DEFAULT_AUDIENCE) -> str | None:
    """Return a cached or freshly-minted Google ID token for ``audience``.

    Returns ``None`` when the metadata server is unreachable (local dev,
    tests, anything outside GCE / Cloud Run) so callers can fall back to a
    transport secret like ``INTERNAL_API_KEY``.
    """
    global _cached_token, _cached_at

    now = time.monotonic()
    if _cached_token and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_token

    async with _lock:
        # Re-check after acquiring the lock so a burst of callers doesn't
        # stampede the metadata server.
        now = time.monotonic()
        if _cached_token and (now - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_token
        token = await _fetch(audience)
        if token is not None:
            _cached_token = token
            _cached_at = now
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
    """Clear the cached token. Tests use this; not part of the public API."""
    global _cached_token, _cached_at
    _cached_token = None
    _cached_at = 0.0
