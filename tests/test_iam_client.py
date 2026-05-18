"""Tests for rozkoduj_mcp.iam_client - Google ID token fetcher.

The module-global cache makes these tests sensitive to ordering, so every
test starts from a clean slate via ``iam_client.reset_cache()``. The
package-level autouse fixture (conftest.py) patches ``iam_client._fetch``
to return ``None`` so other tests don't hit the metadata server; the
fetch-targeted tests below override that patch to exercise the real
``_fetch`` and ``get_id_token`` code paths.
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rozkoduj_mcp import iam_client

# Captured before the package-level autouse fixture replaces _fetch on
# the module, so the original httpx call remains reachable in this file.
_REAL_FETCH = iam_client._fetch


class TestGetIdToken:
    @pytest.mark.anyio
    async def test_returns_cached_token_when_fresh(self) -> None:
        iam_client.reset_cache()
        iam_client._cached_token = "warm-cache-token"  # noqa: S105
        iam_client._cached_at = time.monotonic()
        try:
            # _fetch must not be called; it's already AsyncMock(return_value=None)
            # via the autouse fixture, so any call would return None and bust this.
            assert await iam_client.get_id_token() == "warm-cache-token"
        finally:
            iam_client.reset_cache()

    @pytest.mark.anyio
    async def test_refreshes_when_cache_expired(self) -> None:
        iam_client.reset_cache()
        iam_client._cached_token = "stale-token"  # noqa: S105
        # Force the cache to look ancient.
        iam_client._cached_at = time.monotonic() - 999999.0
        try:
            with patch.object(
                iam_client,
                "_fetch",
                new=AsyncMock(return_value="fresh-token"),
            ):
                assert await iam_client.get_id_token() == "fresh-token"
        finally:
            iam_client.reset_cache()

    @pytest.mark.anyio
    async def test_returns_none_when_fetch_fails(self) -> None:
        iam_client.reset_cache()
        # Autouse fixture already patches _fetch to return None.
        assert await iam_client.get_id_token() is None
        # Cache stays empty so the next call retries instead of pinning None.
        assert iam_client._cached_token is None

    @pytest.mark.anyio
    async def test_double_checked_locking_reuses_first_fetch(self) -> None:
        """A second caller arriving while the first is fetching must see the
        primed cache on its post-lock recheck and skip its own fetch."""
        iam_client.reset_cache()

        fetch_started = asyncio.Event()
        fetch_can_finish = asyncio.Event()
        fetch_count = 0

        async def _slow_fetch(_audience: str) -> str:
            nonlocal fetch_count
            fetch_count += 1
            fetch_started.set()
            await fetch_can_finish.wait()
            return "fetched-once"

        try:
            with patch.object(iam_client, "_fetch", new=_slow_fetch):
                task_first = asyncio.create_task(iam_client.get_id_token())
                # Wait until task_first holds the lock + is blocked in _fetch.
                await fetch_started.wait()
                task_second = asyncio.create_task(iam_client.get_id_token())
                # Give task_second a moment to attempt the fast path and
                # queue at the lock.
                await asyncio.sleep(0)
                # Release the first fetch - it primes the cache and exits.
                fetch_can_finish.set()
                r1, r2 = await asyncio.gather(task_first, task_second)
            assert r1 == "fetched-once"
            # task_second hit the in-lock recheck (line 68) and reused the cache.
            assert r2 == "fetched-once"
            assert fetch_count == 1
        finally:
            iam_client.reset_cache()


class TestFetch:
    """Exercise the real metadata-server call via httpx mocks."""

    @pytest.mark.anyio
    async def test_returns_token_on_success(self) -> None:
        resp = MagicMock()
        resp.text = "id-token-from-metadata"
        resp.raise_for_status = MagicMock()
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(return_value=resp)

        with patch("rozkoduj_mcp.iam_client.httpx.AsyncClient", return_value=client):
            token = await _REAL_FETCH("https://api.example")

        assert token == "id-token-from-metadata"  # noqa: S105
        # The metadata-server contract requires the Metadata-Flavor header.
        call_kwargs: dict[str, Any] = client.get.await_args[1]
        assert call_kwargs["headers"] == {"Metadata-Flavor": "Google"}
        assert call_kwargs["params"] == {"audience": "https://api.example"}

    @pytest.mark.anyio
    async def test_returns_none_on_connect_error(self) -> None:
        """Outside Cloud Run the metadata hostname fails DNS / TCP - the
        return value must be None so callers fall back to INTERNAL_API_KEY.
        """
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(side_effect=httpx.ConnectError("no metadata server"))

        with patch("rozkoduj_mcp.iam_client.httpx.AsyncClient", return_value=client):
            assert await _REAL_FETCH("https://api.example") is None

    @pytest.mark.anyio
    async def test_returns_none_on_empty_body(self) -> None:
        resp = MagicMock()
        resp.text = "   "  # whitespace-only counts as empty
        resp.raise_for_status = MagicMock()
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(return_value=resp)

        with patch("rozkoduj_mcp.iam_client.httpx.AsyncClient", return_value=client):
            assert await _REAL_FETCH("https://api.example") is None

    @pytest.mark.anyio
    async def test_returns_none_on_http_error(self) -> None:
        resp = MagicMock()
        resp.text = "should not be read"
        err = httpx.HTTPStatusError("500", request=MagicMock(), response=resp)
        resp.raise_for_status = MagicMock(side_effect=err)
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        client.get = AsyncMock(return_value=resp)

        with patch("rozkoduj_mcp.iam_client.httpx.AsyncClient", return_value=client):
            assert await _REAL_FETCH("https://api.example") is None


class TestResetCache:
    def test_clears_cached_state(self) -> None:
        iam_client._cached_token = "token"  # noqa: S105
        iam_client._cached_at = time.monotonic()
        iam_client.reset_cache()
        assert iam_client._cached_token is None
        assert iam_client._cached_at == 0.0
